import os
import requests
from flask import Flask, request
from openai import OpenAI, RateLimitError

app = Flask(__name__)

# ========================
# API KEYS
# ========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Prevent duplicate summaries
processed_urls = set()

# ========================
# SEND TELEGRAM MESSAGE
# ========================

def send_message(chat_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }

    requests.post(f"{BASE_URL}/sendMessage", json=payload)


# ========================
# SUMMARIZE ARTICLE
# ========================

def summarize_article(url):

    if url in processed_urls:
        return "Already summarized."

    prompt = f"Summarize this article in 5 concise bullet points:\n{url}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        summary = response.choices[0].message.content
        processed_urls.add(url)

        return summary

    except RateLimitError:
        return "⚠️ OpenAI quota exceeded. Please check billing."

    except Exception as e:
        print("OpenAI error:", e)
        return "⚠️ Summary temporarily unavailable."


# ========================
# GET STOCK INFO
# ========================

def get_stock_info(symbol):

    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "c" not in data:
        return "Stock data unavailable."

    price = data["c"]
    high = data["h"]
    low = data["l"]
    prev_close = data["pc"]

    return f"""
📈 *{symbol} Stock Info*

Current: ${price}
High: ${high}
Low: ${low}
Previous Close: ${prev_close}
"""


# ========================
# HANDLE TELEGRAM WEBHOOK
# ========================

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.json

    # BUTTON PRESSED
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data_value = callback["data"]

        if data_value.startswith("summarize_"):
            url = data_value.replace("summarize_", "")
            summary = summarize_article(url)
            send_message(chat_id, summary)

        elif data_value.startswith("stock_"):
            symbol = data_value.replace("stock_", "")
            stock_info = get_stock_info(symbol)
            send_message(chat_id, stock_info)

        return {"ok": True}

    # NORMAL MESSAGE
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text.lower() == "/start":
            send_message(chat_id, "🤖 AI & Robotics News Bot Activated.")

        if text.lower() == "/test":
            send_message(
                chat_id,
                "Test Article: AI breakthrough in robotics.",
                buttons=[
                    [
                        {"text": "🧠 Summarize", "callback_data": "summarize_https://example.com"},
                        {"text": "📈 Stock Info", "callback_data": "stock_TSLA"}
                    ]
                ]
            )

    return {"ok": True}


# ========================
# RUN SERVER
# ========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
