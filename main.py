import os
import time
import random
import requests
import feedparser
from flask import Flask, request
from openai import OpenAI
from bs4 import BeautifulSoup

app = Flask(__name__)

# =========================
# ENV VARIABLES
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")

if not FINNHUB_KEY:
    raise ValueError("FINNHUB_KEY not set")

client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

latest_articles = {}

# =========================
# SEND MESSAGE
# =========================
def send_message(chat_id, text, buttons=None):
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": False
        }

        if buttons:
            payload["reply_markup"] = {
                "inline_keyboard": buttons
            }

        r = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
        print("TELEGRAM RESPONSE:", r.status_code)

    except Exception as e:
        print("SEND MESSAGE ERROR:", e)


# =========================
# FETCH CLEAN ARTICLE TEXT
# =========================
def fetch_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(r.text, "html.parser")
        paragraphs = soup.find_all("p")

        article_text = " ".join([p.get_text() for p in paragraphs])

        if len(article_text) < 500:
            return None

        return article_text[:6000]

    except Exception as e:
        print("ARTICLE FETCH ERROR:", e)
        return None


# =========================
# SUMMARIZE + DETECT COMPANIES
# =========================
def summarize_and_detect(url):
    article_text = fetch_article_text(url)

    if not article_text:
        return "⚠️ Could not extract readable article content.", []

    prompt = f"""
Summarize this news article in 5 concise bullet points.

Then list publicly traded companies mentioned
with their stock ticker symbols ONLY.

Format exactly:

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
            temperature=0.2
        )

        output = response.choices[0].message.content

        if "COMPANIES:" in output:
            summary_part, companies_part = output.split("COMPANIES:")
            tickers = [
                line.strip()
                for line in companies_part.strip().split("\n")
                if line.strip().isupper()
            ]
        else:
            summary_part = output
            tickers = []

        return summary_part.strip(), tickers[:3]

    except Exception as e:
        print("OPENAI ERROR:", e)
        return "⚠️ Summary unavailable.", []


# =========================
# STOCK INFO
# =========================
def get_stock_info(symbol):
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()

        if not data or "c" not in data:
            return "Stock data unavailable."

        return (
            f"📈 {symbol}\n"
            f"Current: ${data['c']}\n"
            f"High: ${data['h']}\n"
            f"Low: ${data['l']}\n"
            f"Prev Close: ${data['pc']}"
        )

    except Exception as e:
        print("FINNHUB ERROR:", e)
        return "⚠️ Stock info unavailable."


# =========================
# GET AI NEWS
# =========================
def get_ai_news():
    try:
        rss_url = "https://news.google.com/rss/search?q=AI+robotics+China+humanoid+robots&hl=en-US&gl=US&ceid=US:en"

        feed = feedparser.parse(rss_url)

        articles = []

        for entry in feed.entries:
            articles.append((entry.title, entry.link))

        if not articles:
            print("No articles found in RSS feed.")
            return []

        random.shuffle(articles)

        return articles[:7]

    except Exception as e:
        print("RSS ERROR:", e)
        return []


# =========================
# WEBHOOK
# =========================
@app.route(f"/bot{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.json

        if not data:
            return {"ok": True}

        # -------------------------
        # BUTTON CLICK
        # -------------------------
        if "callback_query" in data:
            callback = data["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            callback_data = callback["data"]

            requests.post(
                f"{BASE_URL}/answerCallbackQuery",
                json={"callback_query_id": callback["id"]}
            )

            if callback_data.startswith("summarize_"):
                article_id = int(callback_data.split("_")[1])
                link = latest_articles.get(article_id)

                if link:
                    send_message(chat_id, "🧠 Generating summary...")
                    summary, tickers = summarize_and_detect(link)

                    buttons = []
                    if tickers:
                        row = []
                        for ticker in tickers:
                            row.append({
                                "text": f"📈 {ticker}",
                                "callback_data": f"stock_{ticker}"
                            })
                        buttons.append(row)

                    send_message(chat_id, summary, buttons)
                else:
                    send_message(chat_id, "Article not found.")

            elif callback_data.startswith("stock_"):
                ticker = callback_data.split("_")[1]
                stock_info = get_stock_info(ticker)
                send_message(chat_id, stock_info)

            return {"ok": True}

        # -------------------------
        # MESSAGE HANDLER
        # -------------------------
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")

            if text == "/start":
                send_message(
                    chat_id,
                    "🤖 AI Investment Bot Active.\n\nCommands:\n/news\n/refresh"
                )

            elif text in ["/news", "/refresh"]:
                send_message(chat_id, "Fetching AI & robotics news...")

                latest_articles.clear()
                articles = get_ai_news()

                if not articles:
                    send_message(chat_id, "⚠️ No news articles found.")
                    return {"ok": True}

                for i, (title, link) in enumerate(articles):
                    latest_articles[i] = link

                    send_message(
                        chat_id,
                        f"📰 {title}\n{link}",
                        buttons=[[{
                            "text": "🧠 Summarize",
                            "callback_data": f"summarize_{i}"
                        }]]
                    )

                    time.sleep(0.5)

        return {"ok": True}

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return {"ok": True}


# =========================
# RUN SERVER
# =========================
