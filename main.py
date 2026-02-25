import os
import requests
import feedparser
import random
from flask import Flask, request

app = Flask(__name__)

# Environment Variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY")

# Telegram API URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


# -----------------------
# Helper: Send Telegram Message
# -----------------------
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


# -----------------------
# Helper: Fetch AI News
# -----------------------
def get_ai_news():
    rss_url = "https://news.google.com/rss/search?q=AI+robotics+China+humanoid+robots&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(rss_url)

    articles = []

    for entry in feed.entries:
        articles.append((entry.title, entry.link))

    random.shuffle(articles)

    return articles[:5]


# -----------------------
# Helper: Get Stock Info
# -----------------------
def get_stock_price(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
    response = requests.get(url)
    data = response.json()

    if "c" not in data or data["c"] == 0:
        return None

    return {
        "current": data["c"],
        "high": data["h"],
        "low": data["l"],
        "open": data["o"],
        "previous_close": data["pc"]
    }


# -----------------------
# Health Check Route
# -----------------------
@app.route("/", methods=["GET"])
def health():
    return "SERVER WORKING", 200


# -----------------------
# Telegram Webhook Route
# -----------------------
@app.route(f"/bot{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if not data or "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    # -------- NEWS COMMAND --------
    if text == "/news" or text == "/refresh":
        send_message(chat_id, "Fetching AI & robotics news...")

        articles = get_ai_news()

        if not articles:
            send_message(chat_id, "⚠️ No news articles found.")
            return {"ok": True}

        for title, link in articles:
            send_message(chat_id, f"{title}\n{link}")

    # -------- STOCK COMMAND --------
    elif text.startswith("/stock"):
        parts = text.split()

        if len(parts) < 2:
            send_message(chat_id, "Usage: /stock AAPL")
            return {"ok": True}

        symbol = parts[1].upper()
        stock = get_stock_price(symbol)

        if not stock:
            send_message(chat_id, f"⚠️ Could not fetch data for {symbol}")
            return {"ok": True}

        message = (
            f"📈 {symbol} Stock Info:\n"
            f"Current: ${stock['current']}\n"
            f"High: ${stock['high']}\n"
            f"Low: ${stock['low']}\n"
            f"Open: ${stock['open']}\n"
            f"Previous Close: ${stock['previous_close']}"
        )

        send_message(chat_id, message)

    return {"ok": True}
