import os
import requests
import feedparser
import random
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


def get_ai_news():
    rss_url = "https://news.google.com/rss/search?q=AI+robotics+China+humanoid+robots&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(rss_url)

    articles = []
    for entry in feed.entries:
        articles.append((entry.title, entry.link))

    random.shuffle(articles)
    return articles[:5]


def get_stock_price(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
    response = requests.get(url)
    data = response.json()

    if "c" not in data or data["c"] == 0:
        return None

    return data


@app.route("/", methods=["GET"])
def health():
    return "SERVER WORKING", 200


@app.route(f"/bot{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()

    if not data or "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    if text == "/news" or text == "/refresh":
        send_message(chat_id, "Fetching AI & robotics news...")

        articles = get_ai_news()

        if not articles:
            send_message(chat_id, "No news found.")
            return {"ok": True}

        for title, link in articles:
            send_message(chat_id, f"{title}\n{link}")

    elif text.startswith("/stock"):
        parts = text.split()
        if len(parts) < 2:
            send_message(chat_id, "Usage: /stock AAPL")
            return {"ok": True}

        symbol = parts[1].upper()
        stock = get_stock_price(symbol)

        if not stock:
            send_message(chat_id, f"Could not fetch data for {symbol}")
            return {"ok": True}

        message = (
            f"{symbol} Stock:\n"
            f"Current: ${stock['c']}\n"
            f"High: ${stock['h']}\n"
            f"Low: ${stock['l']}\n"
            f"Open: ${stock['o']}\n"
            f"Previous Close: ${stock['pc']}"
        )

        send_message(chat_id, message)

    return {"ok": True}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
