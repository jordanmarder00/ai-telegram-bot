import os
import time
import requests
import feedparser
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

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
# FETCH ARTICLE TEXT
# ========================

def fetch_article_text(url):
    try:
        r = requests.get(url, timeout=10)
        return r.text[:8000]  # limit size for cost control
    except:
        return None


# ========================
# SUMMARIZE WITH OPENAI
# ========================

def summarize_article(url):
    article_text = fetch_article_text(url)

    if not article_text:
        return "Could not retrieve article content."

    prompt = f"""
Summarize the following news article in 5 concise bullet points.
Focus on business impact, AI relevance, robotics developments,
Chinese company involvement if any, and major breakthroughs.

Article:
{article_text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        return response.choices[0].message.content

    except Exception as e:
        print("OPENAI ERROR:", e)
        return "⚠️ Summary unavailable."


# ========================
# GET AI NEWS
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
                send_message(chat_id, "🧠 Generating summary...")
                summary = summarize_article(link)
                send_message(chat_id, summary)
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
