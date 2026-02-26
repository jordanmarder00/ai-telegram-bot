import os
import time
import requests
import feedparser
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Store articles temporarily
latest_articles = {}

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
    print("TELEGRAM:", r.status_code, r.text)


# ========================
# GET AI NEWS (GOOGLE RSS)
# ========================

def get_ai_news():
    rss_url = "https://news.google.com/rss/search?q=AI+robotics+China+humanoid+robots&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(rss_url)

    articles = []

    for entry in feed.entries[:5]:
        articles.append((entry.title, entry.link))

    return articles


# ========================
# WEBHOOK
# ========================

@app.route(f"/bot{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    print("INCOMING:", data)

    if not data:
        return {"ok": True}

    # BUTTON CLICK
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        callback_data = callback["data"]

        # stop loading spinner
        requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]}
        )

        if callback_data.startswith("summarize_"):
            article_id = int(callback_data.split("_")[1])
            link = latest_articles.get(article_id)

            if link:
                send_message(chat_id, f"🧠 Summary feature coming soon.\n{link}")
            else:
                send_message(chat_id, "Article not found.")

        return {"ok": True}

    # NORMAL MESSAGE
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "🤖 AI & Robotics News Bot Active.")

        elif text == "/news":
            send_message(chat_id, "Fetching latest AI & robotics news...")

            articles = get_ai_news()

            if not articles:
                send_message(chat_id, "No articles found.")
                return {"ok": True}

            latest_articles.clear()

            for i, (title, link) in enumerate(articles):
                latest_articles[i] = link

                send_message(
                    chat_id,
                    f"📰 {title}\n{link}",
                    buttons=[
                        [
                            {
                                "text": "🧠 Summarize",
                                "callback_data": f"summarize_{i}"
                            }
                        ]
                    ]
                )
                time.sleep(0.6)

    return {"ok": True}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
