import os
import requests
import time
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_article(title, url):
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔎 Summarize", "callback_data": f"summary|{url}"},
                {"text": "📈 Stock Info", "callback_data": f"stock|{title}"}
            ]
        ]
    }

    payload = {
        "chat_id": CHAT_ID,
        "text": f"🤖 {title}\n{url}",
        "reply_markup": keyboard
    }

    requests.post(f"{BASE_URL}/sendMessage", json=payload)

def summarize_article(url):
    prompt = f"Summarize this news article in 5 bullet points for an investor:\n{url}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def get_stock_info(company_name):
    # simple example mapping (can improve later)
    mapping = {
        "NVIDIA": "NVDA",
        "Tesla": "TSLA",
        "Baidu": "BIDU",
        "Alibaba": "BABA",
        "Microsoft": "MSFT",
        "Amazon": "AMZN"
    }

    for name in mapping:
        if name.lower() in company_name.lower():
            symbol = mapping[name]
            data = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
            ).json()

            return f"{symbol}\nPrice: {data['c']}\nChange: {data['dp']}%"

    return "No stock data found."

def check_callbacks():
    updates = requests.get(f"{BASE_URL}/getUpdates").json()

    for update in updates.get("result", []):
        if "callback_query" in update:
            data = update["callback_query"]["data"]
            chat_id = update["callback_query"]["message"]["chat"]["id"]

            if data.startswith("summary|"):
                url = data.split("|")[1]
                summary = summarize_article(url)
                requests.post(f"{BASE_URL}/sendMessage",
                              json={"chat_id": chat_id, "text": summary})

            elif data.startswith("stock|"):
                title = data.split("|")[1]
                stock_info = get_stock_info(title)
                requests.post(f"{BASE_URL}/sendMessage",
                              json={"chat_id": chat_id, "text": stock_info})

def get_ai_news():
    url = "https://newsapi.org/v2/everything"
    query = "artificial intelligence OR robotics OR humanoid robot OR china AI"

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 3,
        "apiKey": NEWSAPI_KEY
    }

    response = requests.get(url, params=params).json()
    articles = response.get("articles", [])

    for article in articles:
        send_article(article["title"], article["url"])

send_article("🚀 AI Robotics Intelligence Bot Running", "")

while True:
    get_ai_news()
    check_callbacks()
    time.sleep(300)
