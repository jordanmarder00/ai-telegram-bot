import os
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
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False
    }

    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }

    r = requests.post(f"{BASE_URL}/sendMessage", json=payload)
    print("SEND:", r.status_code, r.text)


# ========================
# GET AI NEWS
# ========================

def get_ai_news():
    url = (
        f"https://newsapi.org/v2/top-headlines?"
        f"category=technology&"
        f"language=en&"
        f"pageSize=5&"
        f"apiKey={NEWS_API_KEY}"
    )

    print("NEWS URL:", url)

    r = requests.get(url)
    print("NEWS STATUS:", r.status_code)
    print("NEWS RESPONSE:", r.text)

    data = r.json()

    articles = []

    for article in data.get("articles", []):
        title = article.get("title")
        link = article.get("url")

        if title and link:
            articles.append((title, link))

    return articles


# ========================
# WEBHOOK
# ========================

@app.route(f"/bot{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    print("WEBHOOK HIT")
    data = request.json
    print("DATA:", data)

    if not data:
        return {"ok": True}

    # BUTTON CLICK
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        callback_data = callback["data"]

        requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]}
        )

        if callback_data.startswith("summarize_"):
            send_message(chat_id, "🧠 Summary feature coming next...")

        return {"ok": True}

    # NORMAL MESSAGE
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "🤖 AI & Robotics News Bot Active.")

        elif text == "/news":
            articles = get_ai_news()

            if not articles:
                send_message(chat_id, "No news found.")
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

        else:
            send_message(chat_id, "Use /news to get AI & robotics updates.")

    return {"ok": True}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

