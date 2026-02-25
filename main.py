import os
import requests
from flask import Flask, request
from openai import OpenAI, RateLimitError

app = Flask(__name__)

# ========================
# ENV VARIABLES
# ========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

processed_urls = set()

# ========================
# SEND TELEGRAM MESSAGE
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

    response = requests.post(f"{BASE_URL}/sendMessage", json=payload)
    print("Telegram response:", response.text)


# ========================
# GET AI NEWS
# ========================

def get_ai_news():
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q=AI OR robotics OR humanoid robot OR artificial intelligence "
        f"OR China AI OR autonomous systems&"
        f"sortBy=publishedAt&language=en&pageSize=5&"
        f"apiKey={NEWS_API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    articles = []

    for article in data.get("articles", [])[:5]:
        title = article["title"]
        link = article["url"]
        articles.append((title, link))

    return articles


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
        return "⚠️ OpenAI quota exceeded."

    except Exception as e:
        print("OpenAI error:", e)
        return "⚠️ Summary unavailable."


# ========================
# GET STOCK INFO
# ========================

def get_stock_info(symbol):
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "c" not in data:
            return "Stock data unavailable."

        return (
            f"📈 {symbol} Stock Info\n\n"
            f"Current: ${data['c']}\n"
            f"High: ${data['h']}\n"
            f"Low: ${data['l']}\n"
            f"Previous Close: ${data['pc']}"
        )

    except Exception as e:
        print("Finnhub error:", e)
        return "⚠️ Stock info unavailable."


# ========================
# TELEGRAM WEBHOOK
# ========================

@app.route(f"/bot{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    print("Incoming update:", data)

    # BUTTON CLICKED
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        callback_data = callback["data"]

        # Stop loading spinner
        requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]}
        )

        if callback_data.startswith("summarize_"):
            url = callback_data.replace("summarize_", "")
            summary = summarize_article(url)
            send_message(chat_id, summary)

        elif callback_data.startswith("stock_"):
            symbol = callback_data.replace("stock_", "")
            stock_info = get_stock_info(symbol)
            send_message(chat_id, stock_info)

        return {"ok": True}

    # NORMAL MESSAGE
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "🤖 AI & Robotics News Bot Activated.")

        elif text == "/test":
            send_message(
                chat_id,
                "📰 Test Article: AI breakthrough in robotics.\nhttps://example.com",
                buttons=[
                    [
                        {
                            "text": "🧠 Summarize",
                            "callback_data": "summarize_https://example.com"
                        },
                        {
                            "text": "📈 Stock Info",
                            "callback_data": "stock_TSLA"
                        }
                    ]
                ]
            )

        elif text == "/news":
            articles = get_ai_news()

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

    return {"ok": True}


# ========================
# RUN SERVER
# ========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
