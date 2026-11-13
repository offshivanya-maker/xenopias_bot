import os
import re
import requests
from bs4 import BeautifulSoup
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
    target_url = f"https://dumpor.com/v/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://dumpor.com/",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"error": f"HTTP Status {response.status_code}"}
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        full_name_elem = soup.find('h1', class_='user__title')
        full_name = full_name_elem.text.strip() if full_name_elem else username
        
        posts, followers, following = "0", "0", "0"
        
        stats = soup.find_all('span', class_='user__stat-value')
        if len(stats) >= 3:
            posts = stats[0].text.strip()
            followers = stats[1].text.strip()
            following = stats[2].text.strip()
            
        og_desc = soup.find('meta', property='og:description')
        if followers == "0" and og_desc and og_desc.get('content'):
            desc = og_desc['content']
            fol_match = re.search(r'([\d,\.KMBkmb]+)\s*Followers', desc, re.I)
            if fol_match: followers = fol_match.group(1)
            fing_match = re.search(r'([\d,\.KMBkmb]+)\s*Following', desc, re.I)
            if fing_match: following = fing_match.group(1)
            post_match = re.search(r'([\d,\.KMBkmb]+)\s*Posts', desc, re.I)
            if post_match: posts = post_match.group(1)

        bio_elem = soup.find('div', class_='user__bio-text')
        bio = bio_elem.text.strip().replace('\n', ' ') if bio_elem else ""

        img_elem = soup.find('img', class_='user__img')
        avatar_url = img_elem['src'] if img_elem and 'src' in img_elem.attrs else ""

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
    return "Dumpor Bot is running!"

if __name__ == '__main__':
    app.run(debug=True)
