import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

app = Flask(__name__)

TG_TOKEN = "8800384691:AAGu4Ipu_NjV0ZLwE2sLBkSXdL8pDAzWi38"

def send_text(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def send_photo(chat_id, photo_url, caption, reply_markup=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = requests.post(url, data=payload)
    return res.json().get("ok", False)

def fetch_instagram_profile(username):
    # Alternative viewer site: GreatFon
    target_url = f"https://greatfon.io/c/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://greatfon.io/"
    }
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"error": f"HTTP Status {response.status_code}"}
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Parsing GreatFon structure
        name_tag = soup.find('div', class_='user__title')
        full_name = name_tag.h1.text.strip() if name_tag and name_tag.h1 else username
        
        posts, followers, following = "0", "0", "0"
        stats = soup.find_all('div', class_='user__number')
        if len(stats) >= 3:
            posts = stats[0].text.strip()
            followers = stats[1].text.strip()
            following = stats[2].text.strip()

        bio_tag = soup.find('div', class_='user__bio')
        bio = bio_tag.text.strip().replace('\n', ' ') if bio_tag else ""

        avatar_tag = soup.find('div', class_='user__img')
        avatar_url = ""
        if avatar_tag and avatar_tag.find('img'):
            avatar_url = avatar_tag.find('img')['src']

        return {
            "username": username,
            "fullName": full_name,
            "posts": posts,
            "followers": followers,
            "following": following,
            "bio": bio,
            "avatarUrl": avatar_url
        }
    except Exception as e:
        return {"error": str(e)}

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data or 'text' not in data['message']:
        return jsonify({"status": "ok"})
        
    chat_id = data['message']['chat']['id']
    text = data['message']['text'].strip()

    if text == "/start":
        send_text(chat_id, "👋 Namaste! Kisi bhi public Instagram profile ka card dekhne ke liye uska username bhejein (jaise: writerofpurefeelings)")
        return jsonify({"status": "ok"})

    username = text.replace("@", "").split(" ")[0]
    if "instagram.com/" in username:
        username = username.split("instagram.com/")[1].split("/")[0].split("?")[0]

    if not username:
        send_text(chat_id, "❌ Kripya sahi username bhejein.")
        return jsonify({"status": "ok"})

    send_text(chat_id, f"⏳ @{username} ka data fetch kiya ja raha hai...")

    profile = fetch_instagram_profile(username)
    
    if not profile or "error" in profile:
        err_msg = profile.get("error", "Unknown error") if profile else "No response"
        send_text(chat_id, f"❌ Data fetch nahi ho paya.\nReason: {err_msg}")
        return jsonify({"status": "ok"})

    card_caption = (
        f"📸 *@{profile['username']}*\n"
        f"*{profile['fullName']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *{profile['posts']}* posts  |  *{profile['followers']}* followers  |  *{profile['following']}* following\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    if profile['bio']:
        card_caption += f"\n📝 *Bio:*\n{profile['bio']}"

    keyboard = {
        "inline_keyboard": [
            [{"text": "🔗 Open Instagram", "url": f"https://instagram.com/{profile['username']}/"}]
        ]
    }

    sent = False
    if profile['avatarUrl']:
        sent = send_photo(chat_id, profile['avatarUrl'], card_caption, keyboard)

    if not sent:
        send_text(chat_id, card_caption, keyboard)

    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def home():
    return "Bot is running!"

if __name__ == '__main__':
    app.run(debug=True)
