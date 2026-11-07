from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from dotenv import load_dotenv
import os
import tempfile
import ai_service
import database as db

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-key")

# ✅ این بخش اینجا اضافه شد تا با gunicorn هم جدول‌ها ساخته بشن
with app.app_context():
    db.init_db()


# ---- توابع کمکی واحد پول ----
def toman_to_rial(toman: int) -> int:
    return int(toman) * 10

def rial_to_toman(rial: int) -> int:
    return int(rial) // 10


@app.route("/")
def index():
    expenses = db.list_expenses(limit=50)
    for e in expenses:
        e["amount_toman"] = rial_to_toman(e["amount"])

    summary = db.get_summary()
    summary_toman = {k: rial_to_toman(v) for k, v in summary.items()}

    breakdown = db.get_category_breakdown(days=30)
    for b in breakdown:
        b["total_toman"] = rial_to_toman(b["total"])

    trend = db.get_daily_trend(days=7)
    for t in trend:
        t["total_toman"] = rial_to_toman(t["total"])

    return render_template(
        "index.html",
        expenses=expenses,
        categories=db.CATEGORIES,
        total_toman=rial_to_toman(db.total_amount()),
        summary=summary_toman,
        breakdown=breakdown,
        trend=trend,
    )


@app.route("/add", methods=["POST"])
def add():
    try:
        amount_toman = int(request.form.get("amount", "0").replace(",", "").strip())
    except ValueError:
        amount_toman = 0

    category = request.form.get("category", "سایر").strip()
    description = request.form.get("description", "").strip()

    if amount_toman <= 0:
        return redirect(url_for("index"))

    db.add_expense(
        amount=toman_to_rial(amount_toman),
        category=category,
        description=description,
    )
    return redirect(url_for("index"))


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete(expense_id: int):
    db.delete_expense(expense_id)
    return redirect(url_for("index"))


@app.get("/api/expenses")
def api_expenses():
    return jsonify(db.list_expenses())


@app.route("/api/voice", methods=["POST"])
def api_voice():
    if "audio" not in request.files:
        return jsonify({"error": "فایل صوتی ارسال نشد"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "نام فایل خالی است"}), 400

    ext = os.path.splitext(audio_file.filename)[1] or ".webm"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            audio_file.save(tmp.name)
            temp_path = tmp.name

        print(f"[voice] received: {audio_file.filename}, size={os.path.getsize(temp_path)} bytes")

        transcript = ai_service.transcribe(temp_path)
        print(f"[voice] transcript: {transcript}")

        result = ai_service.extract_expense(transcript)
        result["raw_transcript"] = transcript

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.route("/sw.js")
def service_worker():
    return send_from_directory(
        app.static_folder, "sw.js", mimetype="application/javascript"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, ssl_context="adhoc")
