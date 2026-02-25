import os
import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=payload)

def get_ai_news():
    url = "https://newsapi.org/v2/everything"
    query = (
        "artificial intelligence OR robotics OR humanoid robot OR "
        "china AI OR semiconductor OR breakthrough AI OR robotics startup"
    )

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": NEWSAPI_KEY
    }

    response = requests.get(url, params=params).json()
    articles = response.get("articles", [])

    if not articles:
        return

    message = "🤖 AI & Robotics Update\n\n"

    for article in articles:
        title = article["title"]
        url = article["url"]
        message += f"- {title}\n{url}\n\n"

    send_message(message)

# Send daily update once when starting
send_message("🚀 AI Robotics Intelligence Bot Running")
get_ai_news()

# Repeat every 6 hours
while True:
    time.sleep(21600)
    get_ai_news()
