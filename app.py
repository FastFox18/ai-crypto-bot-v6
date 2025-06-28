from flask import Flask, request
import os, uuid, requests
from coinbase.rest import RESTClient
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)

# Environment variables
CB_API_KEY = os.getenv("CB_API_KEY")
CB_API_SECRET = os.getenv("CB_API_SECRET")
CB_API_PASSPHRASE = os.getenv("CB_API_PASSPHRASE")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# Coinbase client
client = RESTClient(api_key=CB_API_KEY, api_secret=CB_API_SECRET, passphrase=CB_API_PASSPHRASE)
PRODUCT_ID = "DOGE-USDC"
TRADE_SIZE = "5"

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds.json", scope)
gclient = gspread.authorize(creds)
sheet = gclient.open("CryptoTradeLog").sheet1

def notify_telegram(message):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def log_trade(pair, action, amount, status):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, pair, action, amount, status])

def place_order(side):
    try:
        client.place_market_order(
            client_order_id=str(uuid.uuid4()),
            product_id=PRODUCT_ID,
            side=side.lower(),
            quote_size=TRADE_SIZE
        )
        notify_telegram(f"✅ {side.upper()} order executed for {TRADE_SIZE} USDC")
        log_trade(PRODUCT_ID, side.upper(), TRADE_SIZE, "Success")
    except Exception as e:
        notify_telegram(f"❌ {side.upper()} order failed: {e}")
        log_trade(PRODUCT_ID, side.upper(), TRADE_SIZE, "Fail")

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message", "").upper()
    if "LONG" in message:
        notify_telegram("📈 AI LONG SIGNAL received")
        place_order("BUY")
    elif "SHORT" in message:
        notify_telegram("📉 AI SHORT SIGNAL received")
        place_order("SELL")
    return "OK"

if __name__ == "__main__":
    app.run()