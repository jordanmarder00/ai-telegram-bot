import os
import time
import requests
from flask import Flask, request

app = Flask(__name__)

# ========================
# ENV VARIABLES
# ========================

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
        "text": text,
        "disable_web_page_preview": False
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
# GET AI / ROBOTICS NEWS
# ========================

def get_ai_news():
    print("FETCHING NEWS...")

    url = (
        f"https://newsapi.org/v2/top-headlines?"
        f"category=technology&"
        f"language=en&"
        f"pageSize=20&"
        f"apiKey={NEWS_API_KEY}"
    )

    r = requests.get(url)
    print("NEWS STATUS:", r.status_code)
    print("NEWS RAW:", r.text[:500])  # avoid huge logs

    data = r.json()

    keywords = [
        "ai",
        "artificial intelligence",
        "robot",
        "robotics",
        "humanoid",
        "china",
        "autonomous",
        "machine learning",
        "nvidia",
        "tesla",
        "openai",
        "semiconductor"
    ]

    filtered = []
    fallback = []

    for article in data.get("articles", []):
        title = article.get("title", "")
        link = article.get("url", "")

        if not title or not link:
            continue

        fallback.append((title, link))

        if any(keyword in title.lower() for keyword in keywords):
            filtered.append((title, link))

    print("AI FILTERED:", len(filtered))
    print("FALLBACK:", len(fallback))

    if filtered:
        return filtered[:5]

    return fallback[:5]


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

    # ========================
    # BUTTON CLICK
    # ========================
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        callback_data = callback["data"]

        # stop Telegram loading spinner
        requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]}
        )

        if callback_data.startswith("summarize_"):
            send_message(chat_id, "🧠 Summarization feature coming next...")

        return {"ok": True}

    # ========================
    # NORMAL MESSAGE
    # ========================
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        print("MESSAGE RECEIVED:", text)

        if text == "/start":
            send_message(chat_id, "🤖 AI & Robotics News Bot Active.")

        elif text == "/news":
            send_message(chat_id, "Fetching latest AI & robotics news...")

            articles = get_ai_news()

            if not articles:
                send_message(chat_id, "No articles found.")
                return {"ok": True}

            for title, link in articles:
                send_message(
                    chat_id,
                    f"📰 {title}\n{link}",
                    buttons=[
                        [
                            {
                                "text": "🧠 Summarize",
                                "callback_data": f"summarize_{link}"
                            }
                        ]
                    ]
                )
                time.sleep(0.6)  # prevent Telegram rate limit

        else:
            send_message(chat_id, "Use /news to get AI & robotics updates.")

    return {"ok": True}


# ========================
# RUN SERVER
# ========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
