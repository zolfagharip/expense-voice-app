import ai_service

text = "دیروز ۱۲۰ هزار تومن بنزین زدم"
print("متن ورودی:", text)

result = ai_service.extract_expense(text)
print("خروجی Groq:")
print(result)