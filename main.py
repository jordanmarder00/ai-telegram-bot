import os
import time
import requests
import feedparser
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_KEY")

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
        return r.text[:8000]
    except:
        return None


# ========================
# OPENAI SUMMARY + COMPANY DETECTION
# ========================

def summarize_and_detect(url):
    article_text = fetch_article_text(url)
    if not article_text:
        return "Could not retrieve article content.", []

    prompt = f"""
Summarize this article in 5 concise bullet points.

Then list any publicly traded companies mentioned
with their stock ticker symbols.

Format exactly like this:

SUMMARY:
- bullet
- bullet
- bullet

COMPANIES:
TICKER1
TICKER2

Article:
{article_text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        output = response.choices[0].message.content

        if "COMPANIES:" in output:
            summary_part, companies_part = output.split("COMPANIES:")
            tickers = [
                line.strip()
                for line in companies_part.strip().split("\n")
                if line.strip()
            ]
        else:
            summary_part = output
            tickers = []

        return summary_part.strip(), tickers

    except Exception as e:
        print("OPENAI ERROR:", e)
        return "⚠️ Summary unavailable.", []


# ========================
# STOCK INFO
# ========================

def get_stock_info(symbol):
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
        r = requests.get(url)
        data = r.json()

        if "c" not in data:
            return "Stock data unavailable."

        return (
            f"📈 {symbol}\n"
            f"Current: ${data['c']}\n"
            f"High: ${data['h']}\n"
            f"Low: ${data['l']}\n"
            f"Prev Close: ${data['pc']}"
        )

    except:
        return "⚠️ Stock info unavailable."


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

        requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]}
        )

        # SUMMARY BUTTON
        if callback_data.startswith("summarize_"):
            article_id = int(callback_data.split("_")[1])
            link = latest_articles.get(article_id)

            if link:
                send_message(chat_id, "🧠 Generating summary...")
                summary, tickers = summarize_and_detect(link)

                buttons = []

                if tickers:
                    stock_buttons = []
                    for ticker in tickers[:3]:  # limit to 3
                        stock_buttons.append({
                            "text": f"📈 {ticker}",
                            "callback_data": f"stock_{ticker}"
                        })
                    buttons.append(stock_buttons)

                send_message(chat_id, summary, buttons)
            else:
                send_message(chat_id, "Article not found.")

        # STOCK BUTTON
        elif callback_data.startswith("stock_"):
            ticker = callback_data.split("_")[1]
            stock_info = get_stock_info(ticker)
            send_message(chat_id, stock_info)

        return {"ok": True}

    # NORMAL MESSAGE
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "🤖 AI & Robotics Investment Bot Active.")

        elif text == "/news":
            send_message(chat_id, "Fetching AI & robotics news...")

            articles = get_ai_news()
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
