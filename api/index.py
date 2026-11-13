import os
import io
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TG_TOKEN = "8800384691:AAGtFJQLAlfL3smnat8rSWLuh-5NALMDSPI"

def send_text(chat_id, text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_document(chat_id, content, filename):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument"
    # Create an in-memory file from the response string
    file_obj = io.BytesIO(content.encode('utf-8'))
    file_obj.name = filename
    
    files = {
        'document': (filename, file_obj, 'text/plain')
    }
    data = {
        'chat_id': chat_id,
        'caption': f"📄 Raw HTML Response for {filename}"
    }
    requests.post(url, data=data, files=files)

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data or 'text' not in data['message']:
        return jsonify({"status": "ok"})
        
    chat_id = data['message']['chat']['id']
    text = data['message']['text'].strip()

    if text == "/start":
        send_text(chat_id, "👋 Namaste! Username bhejein, main poora HTML response file banakar bhej dunga.")
        return jsonify({"status": "ok"})

    username = text.replace("@", "").split(" ")[0]
    if "instagram.com/" in username:
        username = username.split("instagram.com/")[1].split("/")[0].split("?")[0]

    send_text(chat_id, f"⏳ @{username} ka raw HTML fetch kiya ja raha hai...")

    target_url = f"https://greatfon.io/c/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://greatfon.io/"
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        raw_html = f"Status Code: {response.status_code}\n\n" + response.text
        
        # Send the complete HTML response as a .txt file on Telegram
        send_document(chat_id, raw_html, f"{username}_response.txt")
        
    except Exception as e:
        send_text(chat_id, f"❌ Error: {str(e)}")

    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def home():
    return "Debug Bot is running!"

if __name__ == '__main__':
    app.run(debug=True)
