import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# إعداد OpenAI API (غادي تاخد المفتاح ديالك وتحطو في Environment Variables في الاستضافة)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# تحقق من الـ Webhook (مهم لربط Meta WhatsApp Cloud API)
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "kla_bot_token")
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Verification token mismatch", 403
    return "Hello, KLA Bot is running!", 200

# استقبال الرسائل من واتساب وإرسالها لـ ChatGPT
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    
    try:
        # استخراج رقم الهاتف ورسالة المستخدم (حسب هيكل Meta Cloud API)
        if "object" in data and data["object"] == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        messages = value["messages"]
                        for msg in messages:
                            phone_number = msg["from"]
                            user_msg = msg["text"]["body"]
                            
                            # صيفط الرسالة لـ ChatGPT
                            ai_response = get_chatgpt_response(user_msg)
                            
                            # صيفط الجواب لواتساب
                            send_whatsapp_message(phone_number, ai_response)
                            
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"}), 500

def get_chatgpt_response(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # تقدر تبدلو ل gpt-4o إذا بغيتي
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"عذراً، حدث خطأ في معالجة الطلب: {str(e)}"

def send_whatsapp_message(to_phone, message_text):
    # إعدادات Meta Cloud API لإرسال الرسائل
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
    PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
    
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": message_text}
    }
    
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
