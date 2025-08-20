import logging
import requests
import csv
import os
import random
import asyncio
from flask import Flask, request
from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Load .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
SEND_DOCUMENT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    logger.info(f"Update received: {data}")

    update = Update.de_json(data, application.bot)
    application.process_update(update)
    return "ok", 200


def fetch_groww_mtf_data():
    base_url = "https://groww.in/v1/api/mtf/approved_mtf_stocks"
    page, limit = 0, 50
    all_data = []

    while True:
        try:
            response = requests.get(base_url, params={
                "limit": limit, "order": "ASC", "page": page, "query": "", "sort": "COMPANY_NAME"
            })
            response.raise_for_status()
            data = response.json().get("data", [])
            if not data:
                break
            for s in data:
                if s.get("marketCap", 0) == 0:
                    continue
                all_data.append({
                    "companyName": s["companyName"],
                    "symbolIsin": s["symbolIsin"],
                    "leverage": s["leverage"],
                    "searchId": s.get("searchId"),
                })
            page += 1
        except Exception as e:
            logger.error(f"Error fetching MTF data: {e}")
            break
    return all_data

def save_to_csv(data, filename):
    if not data:
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def handle_mtf_download_sync(chat_id):
    """Blocking function to fetch data, save CSVs, and send files via Telegram HTTP API."""
    data = fetch_groww_mtf_data()
    if not data:
        requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": "Failed to fetch MTF data."})
        return

    leverage_2_to_3 = [d for d in data if 2 <= d["leverage"] <= 3]
    leverage_3_to_4 = [d for d in data if 3 <= d["leverage"] <= 4]

    file1 = "groww_mtf_leverage_2_to_3.csv"
    file2 = "groww_mtf_leverage_3_to_4.csv"

    save_to_csv(leverage_2_to_3, file1)
    save_to_csv(leverage_3_to_4, file2)

    for f in [file1, file2]:
        with open(f, "rb") as doc:
            requests.post(SEND_DOCUMENT_URL, data={"chat_id": chat_id}, files={"document": doc})
        os.remove(f)

    requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": "MTF files sent!"})


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Swing trade", callback_data="swing_trade")],
        [InlineKeyboardButton("Long Term", callback_data="long_term")],
        [InlineKeyboardButton("Download Grow MTF Data", callback_data="download_mtf")],
        [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(f"Hi {user.full_name}!\nChoose an option:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(f"Hi {user.full_name}!\nChoose an option:", reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_main_menu(update, context)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        await query.answer()
        choice = query.data

        back_button = InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")
        back_markup = InlineKeyboardMarkup([[back_button]])

        if choice == "swing_trade":
            await query.edit_message_text("Swing Trading: short to medium-term price moves.", reply_markup=back_markup)
            await query.message.reply_photo(
                photo=f"https://picsum.photos/600/400?random={random.randint(1,1000)}",
                reply_markup=back_markup,
            )

        elif choice == "long_term":
            await query.edit_message_text("Long-Term Investing: buy and hold for years.", reply_markup=back_markup)
            await query.message.reply_photo(
                photo=f"https://picsum.photos/600/400?random={random.randint(1,1000)}",
                reply_markup=back_markup,
            )

        elif choice == "download_mtf":
            await query.edit_message_text("Fetching MTF data... This may take a while.", reply_markup=back_markup)
            chat_id = query.message.chat.id
            # Run the blocking download function in executor to avoid blocking event loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, handle_mtf_download_sync, chat_id)

        elif choice == "back_to_menu":
            await send_main_menu(update, context)

    except Exception as e:
        logger.error(f"Error in button_click handler: {e}")
        await query.message.reply_text("Oops! Something went wrong, please try again.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Unknown message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text(
        "Unknown command. Please use /start or choose from the menu.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")]]
        ),
    )


if __name__ == "__main__":
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    # If you want polling (for testing), uncomment below:
    # application.run_polling()

    # For webhook, run Flask app:
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
