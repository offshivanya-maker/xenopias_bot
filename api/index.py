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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    # List of alternative viewer sites to try sequentially (Fallback mechanism)
    urls = [
        f"https://greatfon.io/c/{username}",
        f"https://www.picuki.com/profile/{username}",
        f"https://imginn.com/{username}/"
    ]

    for target_url in urls:
        try:
            response = requests.get(target_url, headers=headers, timeout=8)
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            og_title = soup.find('meta', property='og:title')
            og_desc = soup.find('meta', property='og:description')
            og_image = soup.find('meta', property='og:image')
            
            if not og_desc and not og_title:
                continue

            full_name = username
            if og_title and og_title.get('content'):
                title_content = og_title['content']
                if '(' in title_content and ')' in title_content:
                    full_name = title_content.split('(')[0].strip()
                elif '-' in title_content:
                    full_name = title_content.split('-')[0].strip()

            avatar_url = ""
            if og_image and og_image.get('content'):
                avatar_url = og_image['content']

            posts, followers, following = "0", "0", "0"
            bio = ""

            if og_desc and og_desc.get('content'):
                desc = og_desc['content']
                
                # Extract metrics using regex from description meta tag
                fol_match = re.search(r'([\d,\.KMBkmb]+)\s*Followers', desc, re.I)
                if fol_match: followers = fol_match.group(1)
                
                fing_match = re.search(r'([\d,\.KMBkmb]+)\s*Following', desc, re.I)
                if fing_match: following = fing_match.group(1)
                
                post_match = re.search(r'([\d,\.KMBkmb]+)\s*Posts', desc, re.I)
                if post_match: posts = post_match.group(1)
                
                parts = re.split(r'[-–—]\s*', desc, 1)
                if len(parts) > 1:
                    bio = parts[1].strip()

            # If we successfully extracted followers or posts, return the data
            if followers != "0" or posts != "0" or bio != "":
                return {
                    "username": username,
                    "fullName": full_name,
                    "posts": posts,
                    "followers": followers,
                    "following": following,
                    "bio": bio,
                    "avatarUrl": avatar_url
                }
        except Exception:
            continue

    return {"error": "All viewer nodes blocked or unavailable."}

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
    return "Multi-Node Fallback Bot is running!"

if __name__ == '__main__':
    app.run(debug=True)
