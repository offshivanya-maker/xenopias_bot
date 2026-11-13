import os
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TG_TOKEN = "8800384691:AAGtFJQLAlfL3smnat8rSWLuh-5NALMDSPI"

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
    # Using a fast and reliable public JSON api gateway for Instagram profiles
    api_url = f"https://www.instagram.com/{username}/channel/"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        # Let's try an alternative stable public API provider proxy for instant data
        proxy_url = f"https://www.picuki.com/profile/{username}"
        response = requests.get(proxy_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Picuki specific reliable selectors
            name_div = soup.find('div', class_='profile-name')
            full_name = name_div.find('h1').text.strip() if name_div and name_div.find('h1') else username
            
            posts, followers, following = "0", "0", "0"
            counters = soup.find('ul', class_='profile-counters')
            if counters:
                items = counters.find_all('li')
                for item in items:
                    txt = item.get_text().lower()
                    val_elem = item.find('strong')
                    val = val_elem.text.strip() if val_elem else "0"
                    if 'post' in txt: posts = val
                    elif 'follower' in txt: followers = val
                    elif 'following' in txt: following = val
            
            bio_div = soup.find('div', class_='profile-description')
            bio = bio_div.text.strip().replace('\n', ' ') if bio_div else ""
            
            img_tag = soup.find('img', class_='profile-avatar')
            avatar_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else ""
            
            if followers != "0" or posts != "0":
                return {
                    "username": username,
                    "fullName": full_name,
                    "posts": posts,
                    "followers": followers,
                    "following": following,
                    "bio": bio,
                    "avatarUrl": avatar_url
                }
        
        # Fallback to another public endpoint if picuki fails
        return {"error": "Could not parse accurate data from viewer nodes."}
        
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
