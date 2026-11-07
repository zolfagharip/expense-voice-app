import os
import json
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

# خواندن .env از کنار همین فایل
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ALLOWED_CATEGORIES = [
    "بنزین", "خوراک", "قهوه", "حمل‌ونقل", "خرید",
    "قبض", "سلامت", "سرگرمی", "سایر",
]

# اصلاح اشتباهات رایج Whisper در فارسی
_WHISPER_FIXES = {
    "ست هزار": "صد هزار",
    "ست تومان": "صد تومان",
    "چارصد": "چهارصد",
    "چار هزار": "چهار هزار",
    "پونصد": "پانصد",
    "نصد": "نهصد",
    "شص": "شصت",
}


def _fix_transcript(text: str) -> str:
    """اصلاح اشتباهات رایج Whisper در فارسی"""
    for wrong, right in _WHISPER_FIXES.items():
        text = text.replace(wrong, right)
    return text


def transcribe(audio_file_path: str) -> str:
    """فایل صوتی رو به متن فارسی تبدیل می‌کنه."""
    with open(audio_file_path, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_file_path), file.read()),
            model="whisper-large-v3",
            language="fa",
            response_format="text",
        )
    text = transcription.strip()
    return _fix_transcript(text)


def extract_expense(text: str) -> dict:
    """از متن، مبلغ (به تومان) و دسته‌بندی رو استخراج می‌کنه."""
    if not text or not text.strip():
        return {"amount": 0, "category": "سایر", "description": "", "confidence": 0.0}

    system_prompt = f"""
تو یک دستیار مالی فارسی‌زبان هستی. متن کاربر را تحلیل کن و اطلاعات هزینه را به صورت JSON برگردان.

قوانین حیاتی:
1. مبلغ را به "تومان" برگردان.
2. اعداد فارسی/لفظی را به عدد صحیح تبدیل کن:
   - "صد هزار" یا "۱۰۰ هزار" = 100000
   - "دویست هزار" = 200000
   - "سیصد هزار" = 300000
   - "چهارصد هزار" = 400000
   - "پانصد هزار" = 500000
   - "ششصد هزار" = 600000
   - "هفتصد هزار" = 700000
   - "هشتصد هزار" = 800000
   - "نهصد هزار" = 900000
   - "یک میلیون" = 1000000
   - "یک و نیم میلیون" یا "یک میلیون و پانصد" = 1500000
   - اگر مبلغ به "هزار" بود، در ۱۰۰۰ ضرب کن.
3. اگر مبلغ مبهم بود، مقدار 0 بگذار.
4. دسته‌بندی را دقیقاً از این لیست انتخاب کن: {', '.join(ALLOWED_CATEGORIES)}
5. فیلد description همان متن اصلی کاربر باشد.
6. فیلد confidence را بین 0 تا 1 قرار بده.

مثال‌ها:
- "صد هزار تومن قهوه خریدم" → {{"amount": 100000, "category": "قهوه", "description": "صد هزار تومن قهوه خریدم", "confidence": 0.95}}
- "دویست و پنجاه هزار بنزین" → {{"amount": 250000, "category": "بنزین", "description": "دویست و پنجاه هزار بنزین", "confidence": 0.9}}
- "یک میلیون و پانصد خرید" → {{"amount": 1500000, "category": "خرید", "description": "یک میلیون و پانصد خرید", "confidence": 0.9}}

فقط و فقط JSON برگردان، هیچ متن اضافه‌ای ننویس.
فرمت خروجی:
{{"amount": 120000, "category": "بنزین", "description": "متن", "confidence": 0.95}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=500,
    )

    try:
        data = json.loads(response.choices[0].message.content)
        if data.get("category") not in ALLOWED_CATEGORIES:
            data["category"] = "سایر"
        return data
    except Exception as e:
        print(f"JSON parse error: {e}")
        return {"amount": 0, "category": "سایر", "description": text, "confidence": 0.0}