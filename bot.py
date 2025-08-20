import os
import requests
import datetime
import csv
import yfinance as yf
import matplotlib.pyplot as plt
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Bot and Flask Setup ---
TOKEN = os.getenv("BOT_TOKEN")
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# --- Helper Functions ---
def back_to_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])

def generate_chart(stock_type, symbol="RELIANCE.NS"):
    # Define time range
    if stock_type.lower() == "swing":
        start_date = datetime.datetime.now() - datetime.timedelta(days=14)
        interval = "1h"
    else:  # long term
        start_date = datetime.datetime.now() - datetime.timedelta(days=180)
        interval = "1d"

    end_date = datetime.datetime.now()

    # Fetch data
    data = yf.download(symbol, start=start_date, end=end_date, interval=interval)

    if data.empty:
        return None

    # Plot chart
    plt.figure(figsize=(10, 5))
    plt.plot(data.index, data["Close"], label="Close Price", color="blue")
    plt.title(f"{symbol} - {stock_type.title()} Trade Chart")
    plt.xlabel("Date")
    plt.ylabel("Price (INR)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    filename = f"{stock_type.lower()}_{symbol.replace('.', '_')}_chart.png"
    plt.savefig(filename)
    plt.close()
    return filename

def fetch_groww_mtf_data():
    base_url = "https://groww.in/v1/api/mtf/approved_mtf_stocks"
    page = 0
    limit = 50
    all_data = []

    while True:
        params = {
            "limit": limit,
            "order": "ASC",
            "page": page,
            "query": "",
            "sort": "COMPANY_NAME"
        }
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            break

        json_data = response.json()
        stocks = json_data.get("data", [])

        if not stocks:
            break

        for stock in stocks:
            market_cap = stock.get("marketCap", 0.0)
            leverage = stock.get("leverage", 0.0)
            if market_cap == 0:
                continue

            all_data.append({
                "companyName": stock.get("companyName"),
                "symbolIsin": stock.get("symbolIsin"),
                "leverage": leverage,
                "searchId": stock.get("searchId"),
            })

        page += 1

    return all_data

def save_to_csv(data, filename):
    if not data:
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def generate_mtf_csv_files():
    mtf_data = fetch_groww_mtf_data()
    leverage_2_to_3 = [stock for stock in mtf_data if 2 <= stock["leverage"] <= 3]
    leverage_3_to_4 = [stock for stock in mtf_data if 3 <= stock["leverage"] <= 4]

    file1 = "groww_mtf_leverage_2_to_3.csv"
    file2 = "groww_mtf_leverage_3_to_4.csv"

    save_to_csv(leverage_2_to_3, file1)
    save_to_csv(leverage_3_to_4, file2)

    return [file1, file2]

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📈 Swing Trade", callback_data="swing")],
        [InlineKeyboardButton("📊 Long Term Trade", callback_data="longterm")],
        [InlineKeyboardButton("📥 Download Groww MTF Data", callback_data="download")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to StockBot! Choose an option:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "swing":
        chart = generate_chart("Swing")
        if chart:
            await query.edit_message_text(f"Here is your Swing Trade chart:", reply_markup=back_to_menu_keyboard())
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(chart, "rb"))
        else:
            await query.edit_message_text("No data found for the requested stock.", reply_markup=back_to_menu_keyboard())
    elif query.data == "longterm":
        chart = generate_chart("Long Term")
        if chart:
            await query.edit_message_text(f"Here is your Long Term Trade chart:", reply_markup=back_to_menu_keyboard())
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(chart, "rb"))
        else:
            await query.edit_message_text("No data found for the requested stock.", reply_markup=back_to_menu_keyboard())
    elif query.data == "download":
        files = generate_mtf_csv_files()
        await query.edit_message_text("Here are your Groww MTF files:", reply_markup=back_to_menu_keyboard())
        for file in files:
            await context.bot.send_document(chat_id=query.message.chat_id, document=open(file, "rb"))
            os.remove(file) # Clean up the generated file
    elif query.data == "back":
        await query.edit_message_text("Welcome to StockBot! Choose an option:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 Swing Trade", callback_data="swing")],
            [InlineKeyboardButton("📊 Long Term Trade", callback_data="longterm")],
            [InlineKeyboardButton("📥 Download Groww MTF Data", callback_data="download")]
        ]))

# --- Register Handlers ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_button))

# --- Flask Webhook ---
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    await application.update_queue.put(Update.de_json(request.get_json(force=True), application.bot))
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))