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

print("BOT TOKEN LOADED:", TELEGRAM_TOKEN is not None)

client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

processed_urls = set()

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

    try:
        r = requests.post(f"{BASE_URL}/sendMessage", json=payload)
        print("SEND MESSAGE RESPONSE:", r.status_code, r.text)
    except Exception as e:
        print("SEND MESSAGE ERROR:", e)


# ========================
# WEBHOOK
# ========================

@app.route(f"/bot{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    print("WEBHOOK HIT")

    data = request.json
    print("INCOMING DATA:", data)

    if not data:
        return {"ok": True}

    # BUTTON CLICK
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        callback_data = callback["data"]

        print("BUTTON CLICKED:", callback_data)

        requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]}
        )

        send_message(chat_id, f"You clicked: {callback_data}")
        return {"ok": True}

    # NORMAL MESSAGE
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        print("MESSAGE RECEIVED:", text)

        if text == "/start":
            send_message(chat_id, "Bot is alive ✅")

        elif text == "/test":
            send_message(
                chat_id,
                "Test working.",
                buttons=[
                    [
                        {
                            "text": "Click Me",
                            "callback_data": "test_button"
                        }
                    ]
                ]
            )

        else:
            send_message(chat_id, f"You said: {text}")

    return {"ok": True}


# ========================
# RUN SERVER
# ========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
