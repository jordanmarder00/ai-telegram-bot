import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ========================
# SEND MESSAGE
# ========================

def send_message(chat_id, text, buttons=None):
    print("SENDING MESSAGE TO:", chat_id)

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }

    try:
        r = requests.post(f"{BASE_URL}/sendMessage", json=payload)
        print("TELEGRAM RESPONSE:", r.status_code, r.text)
    except Exception as e:
        print("SEND ERROR:", e)


# ========================
# GET NEWS
# ========================

def get_ai_news():
    print("FETCHING NEWS...")

    url = (
        f"https://newsapi.org/v2/top-headlines?"
        f"category=technology&"
        f"language=en&"
        f"pageSize=5&"
        f"apiKey={NEWS_API_KEY}"
    )

    r = requests.get(url)
    print("NEWS STATUS:", r.status_code)
    print("NEWS RAW:", r.text)

    data = r.json()
    articles = []

    for article in data.get("articles", []):
        title = article.get("title")
        link = article.get("url")

        if title and link:
            articles.append((title, link))

    print("ARTICLES FOUND:", len(articles))
    return articles


# ========================
# WEBHOOK
# ========================

@app.route(f"/bot{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    print("WEBHOOK HIT")

    data = request.json
    print("INCOMING DATA:", data)

    if not data:
        return {"ok": True}

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        print("MESSAGE RECEIVED:", text)

        if text == "/start":
            send_message(chat_id, "Bot alive ✅")

        elif text == "/news":
            send_message(chat_id, "Getting news...")

            articles = get_ai_news()

            if not articles:
                send_message(chat_id, "No articles returned from API.")
                return {"ok": True}

            for title, link in articles:
                send_message(chat_id, f"📰 {title}\n{link}")

        else:
            send_message(chat_id, "Command not recognized.")

    return {"ok": True}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
