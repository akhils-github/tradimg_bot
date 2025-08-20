import os
import requests
import datetime
import csv
import yfinance as yf
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
from concurrent.futures import ThreadPoolExecutor
import tempfile

load_dotenv()

# --- Bot and Flask Setup ---
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app-url.herokuapp.com")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# Create an executor for running async functions
executor = ThreadPoolExecutor()

# Set matplotlib to use Agg backend for server environments
plt.switch_backend('Agg')

# --- Helper Functions ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📈 Swing Trade", callback_data="swing")],
        [InlineKeyboardButton("📊 Long Term Trade", callback_data="longterm")],
        [InlineKeyboardButton("📥 Download Groww MTF Data", callback_data="download")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])

def generate_chart(stock_type, symbol="RELIANCE.NS"):
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    filename = temp_file.name
    temp_file.close()
    
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
        os.unlink(filename)  # Remove the temp file
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
        try:
            response = requests.get(base_url, params=params, timeout=10)
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
        except requests.RequestException:
            break

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

    # Create temporary files
    file1 = tempfile.NamedTemporaryFile(suffix='.csv', delete=False).name
    file2 = tempfile.NamedTemporaryFile(suffix='.csv', delete=False).name

    save_to_csv(leverage_2_to_3, file1)
    save_to_csv(leverage_3_to_4, file2)

    return [file1, file2]

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start command received!")
    await update.message.reply_text("Welcome to StockBot! Choose an option:", reply_markup=main_menu_keyboard())

async def show_loading(query, text="Processing your request..."):
    """Show a loading message"""
    loading_text = f"⏳ {text}"
    await query.edit_message_text(loading_text)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Show loading message
    if query.data == "swing":
        await show_loading(query, "Generating Swing Trade chart...")
        chart = generate_chart("Swing")
        if chart:
            # Send the chart with back button
            with open(chart, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id, 
                    photo=photo,
                    caption="📈 Swing Trade Chart\n\nClick 🔙 to return to menu",
                    reply_markup=back_to_menu_keyboard()
                )
            os.unlink(chart)  # Clean up the generated file
        else:
            await query.edit_message_text(
                "❌ No data found for the requested stock.",
                reply_markup=back_to_menu_keyboard()
            )
    
    elif query.data == "longterm":
        await show_loading(query, "Generating Long Term Trade chart...")
        chart = generate_chart("Long Term")
        if chart:
            # Send the chart with back button
            with open(chart, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id, 
                    photo=photo,
                    caption="📊 Long Term Trade Chart\n\nClick 🔙 to return to menu",
                    reply_markup=back_to_menu_keyboard()
                )
            os.unlink(chart)  # Clean up the generated file
        else:
            await query.edit_message_text(
                "❌ No data found for the requested stock.",
                reply_markup=back_to_menu_keyboard()
            )
    
    elif query.data == "download":
        await show_loading(query, "Fetching Groww MTF data...")
        files = generate_mtf_csv_files()
        
        # Send files with back button
        for file in files:
            try:
                with open(file, "rb") as doc:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id, 
                        document=doc,
                        caption="📥 Groww MTF Data" + ("\n\nClick 🔙 to return to menu" if file == files[-1] else "")
                    )
            except FileNotFoundError:
                await query.edit_message_text(
                    "❌ Error: File not found. Please try again.",
                    reply_markup=back_to_menu_keyboard()
                )
                return
            finally:
                # Clean up the file
                if os.path.exists(file):
                    os.unlink(file)
        
        # Send back button only after the last file
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Download complete!",
            reply_markup=back_to_menu_keyboard()
        )
    
    elif query.data == "back":
        # Return to main menu by sending a new message
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Welcome to StockBot! Choose an option:",
            reply_markup=main_menu_keyboard()
        )

# --- Register Handlers ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_button))

# Function to run async code in a thread
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- Flask Webhook ---
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    """Handle incoming updates from Telegram"""
    try:
        update = Update.de_json(request.get_json(), application.bot)
        # Run the async function in a thread
        executor.submit(run_async, application.process_update(update))
        return "ok"
    except Exception as e:
        print(f"Error processing update: {e}")
        return "error", 500

@app.route("/")
def index():    
    return "Bot is running! Visit /set_webhook to configure the webhook."

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """Set webhook for Telegram bot"""
    try:
        # Set webhook
        url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
        result = run_async(application.bot.set_webhook(url))
        if result:
            return jsonify({"status": "success", "message": f"Webhook set to {url}"})
        else:
            return jsonify({"status": "error", "message": "Failed to set webhook"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/remove_webhook", methods=["GET"])
def remove_webhook():
    """Remove webhook for Telegram bot"""
    try:
        result = run_async(application.bot.delete_webhook())
        if result:
            return jsonify({"status": "success", "message": "Webhook removed"})
        else:
            return jsonify({"status": "error", "message": "Failed to remove webhook"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    # For production with webhooks
    application.run_polling()
    # port = int(os.environ.get("PORT", 5000))
    # app.run(debug=False, host="0.0.0.0", port=port)