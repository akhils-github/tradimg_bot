import logging
import requests
import csv
import os
import random
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

# Load environment variables from .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
SEND_DOCUMENT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"

# --- Logging setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Flask app ---
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running"


@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").lower()

        if "mtf" in text or "download" in text:
            mtf_data = fetch_groww_mtf_data()

            if not mtf_data:
                requests.post(
                    TELEGRAM_API_URL,
                    json={"chat_id": chat_id, "text": "Failed to fetch data."},
                )
                return "ok", 200

            leverage_2_to_3 = [s for s in mtf_data if 2 <= s["leverage"] <= 3]
            leverage_3_to_4 = [s for s in mtf_data if 3 <= s["leverage"] <= 4]

            file_2_to_3 = "groww_mtf_leverage_2_to_3.csv"
            file_3_to_4 = "groww_mtf_leverage_3_to_4.csv"

            save_to_csv(leverage_2_to_3, file_2_to_3)
            save_to_csv(leverage_3_to_4, file_3_to_4)

            for file_path in [file_2_to_3, file_3_to_4]:
                with open(file_path, "rb") as f:
                    requests.post(
                        SEND_DOCUMENT_URL,
                        data={"chat_id": chat_id},
                        files={"document": f},
                    )

            reply = "MTF data files sent!"
            requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": reply})

            # Cleanup
            os.remove(file_2_to_3)
            os.remove(file_3_to_4)

        else:
            reply = f"You said: {text}\nSend 'mtf' to fetch MTF data."
            requests.post(TELEGRAM_API_URL, json={"chat_id": chat_id, "text": reply})

    return "ok", 200


# --- Groww MTF Data Fetcher ---
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
            "sort": "COMPANY_NAME",
        }
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            json_data = response.json()
            stocks = json_data.get("data", [])

            if not stocks:
                break

            for stock in stocks:
                try:
                    market_cap = stock.get("marketCap", 0.0)
                    leverage = stock.get("leverage", 0.0)
                    if market_cap == 0:
                        continue

                    all_data.append(
                        {
                            "companyName": stock["companyName"],
                            "symbolIsin": stock["symbolIsin"],
                            "leverage": leverage,
                            "searchId": stock.get("searchId"),
                        }
                    )
                except KeyError as e:
                    logger.error(f"Missing key: {e}")
                    continue

            logger.info(f"Fetched page {page} with {len(stocks)} stocks")
            page += 1
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            break

    return all_data


def save_to_csv(data, filename):
    if not data:
        logger.warning(f"No data to save: {filename}")
        return

    fieldnames = data[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"Saved {len(data)} records to {filename}")


# --- Telegram Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Swing trade", callback_data="swing_trade")],
        [InlineKeyboardButton("Long Term", callback_data="long_term")],
        [InlineKeyboardButton("Download Grow MTF Data", callback_data="download_mtf")],
        [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Hi {user.full_name}!\n\nPlease choose an option:", reply_markup=reply_markup
    )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    choice = query.data

    back_button = InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")
    back_markup = InlineKeyboardMarkup([[back_button]])

    if choice == "swing_trade":
        await query.edit_message_text(
            "Swing Trading involves short to medium-term price moves.",
            reply_markup=back_markup,
        )
        await query.message.reply_photo(
            photo=f"https://picsum.photos/600/400?random={random.randint(1,999)}",
            reply_markup=back_markup,
        )

    elif choice == "long_term":
        await query.edit_message_text(
            "Long-term investing focuses on years of holding assets.",
            reply_markup=back_markup,
        )
        await query.message.reply_photo(
            photo=f"https://picsum.photos/600/400?random={random.randint(1,999)}",
            reply_markup=back_markup,
        )

    elif choice == "download_mtf":
        await query.edit_message_text(
            "Fetching data and generating files... Please wait.",
            reply_markup=back_markup,
        )

        mtf_data = fetch_groww_mtf_data()

        if not mtf_data:
            await query.edit_message_text(
                "Failed to fetch data.", reply_markup=back_markup
            )
            return

        leverage_2_to_3 = [s for s in mtf_data if 2 <= s["leverage"] <= 3]
        leverage_3_to_4 = [s for s in mtf_data if 3 <= s["leverage"] <= 4]

        file_2_to_3 = "groww_mtf_leverage_2_to_3.csv"
        file_3_to_4 = "groww_mtf_leverage_3_to_4.csv"

        save_to_csv(leverage_2_to_3, file_2_to_3)
        save_to_csv(leverage_3_to_4, file_3_to_4)

        try:
            await query.message.reply_document(document=open(file_2_to_3, "rb"))
            await query.message.reply_document(document=open(file_3_to_4, "rb"))
            await query.message.reply_text(
                "Files sent successfully!", reply_markup=back_markup
            )
        except Exception as e:
            logger.error(f"Error sending files: {e}")
            await query.message.reply_text(
                "Error sending files.", reply_markup=back_markup
            )

        os.remove(file_2_to_3)
        os.remove(file_3_to_4)

    elif choice == "back_to_menu":
        await back_to_menu(update, context)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Sorry, I didn't understand that.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")]]
        ),
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Swing trade", callback_data="swing_trade")],
        [InlineKeyboardButton("Long Term", callback_data="long_term")],
        [InlineKeyboardButton("Download Grow MTF Data", callback_data="download_mtf")],
        [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        f"Hi {user.full_name}! Choose an option:", reply_markup=reply_markup
    )


# --- Main ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not found in environment variables")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    # For local testing, use polling
    application.run_polling()
