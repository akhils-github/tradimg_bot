import logging
import requests
import csv
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import random
from dotenv import load_dotenv

from aiohttp import web

# Load environment variables from .env file
load_dotenv()
# Access the BOT_TOKEN from the environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Flask app to handle port binding

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)



#  Aiohttp Webhook Setup
async def telegram_webhook_handler(request):
    """Handle incoming Telegram updates."""
    # This handler needs access to the 'application' object.
    # We will get it from the aiohttp application state.
    app = request.app
    application = app['bot_app']

    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(text="ok")
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return web.Response(text="error", status=500)

async def main():
    """Builds and runs the aiohttp server with the Telegram bot application."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not found in environment variables")
    
    # 1. Initialize the python-telegram-bot application correctly
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 2. Add your handlers to the application instance
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    # 3. Create the aiohttp application and store the bot application in its state
    app = web.Application()
    app['bot_app'] = application
    app.router.add_post('/webhook', telegram_webhook_handler)

    # 4. Return the configured aiohttp application
    return app

if __name__ == "__main__":
    # This is the correct entry point to run the aiohttp server.
    web.run_app(main())
# --- Data fetching and file saving functions ---


def fetch_groww_mtf_data():
    """
    Fetches Margin Trading Facility (MTF) data from Groww API.
    """
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
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            json_data = response.json()
            stocks = json_data.get("data", [])

            if not stocks:
                break

            for stock in stocks:
                try:
                    market_cap = stock.get("marketCap", 0.0)
                    leverage = stock.get("leverage", 0.0)

                    # Skip stocks with zero market cap
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
                    logger.error(f"Missing key in stock data: {e} for stock: {stock}")
                    continue

            logger.info(f"Fetched page {page} with {len(stocks)} records")
            page += 1
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {page}: {e}")
            break

    return all_data


def save_to_csv(data, filename):
    """
    Saves a list of dictionaries to a CSV file.
    """
    if not data:
        logger.warning(f"No data to save in {filename}.")
        return

    fieldnames = data[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"Saved {len(data)} records to {filename}")


# --- Handlers for the commands and messages ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a list of options with inline buttons."""
    user = update.effective_user

    # Define inline buttons for the options
    keyboard = [
        [InlineKeyboardButton("Swing trade", callback_data="swing_trade")],
        [InlineKeyboardButton("Long Term", callback_data="long_term")],
        [InlineKeyboardButton("Download Grow MTF Data", callback_data="download_mtf")],
        [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with inline buttons
    await update.message.reply_text(
        f"Hi {user.full_name}!\n\nPlease choose an option:", reply_markup=reply_markup
    )


# CallbackQueryHandler functions for each option
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button click events."""
    query = update.callback_query
    # Try to acknowledge the button click immediately to avoid timeout errors
    try:
        await query.answer()
    except Exception as e:
        logger.warning(
            f"CallbackQuery answer failed: {e}"
        )  # Acknowledge the button click to prevent it from hanging.

    choice = query.data

    # Define the Back to Menu button for every response
    back_button = InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")
    back_button_markup = InlineKeyboardMarkup([[back_button]])

    if choice == "swing_trade":
        # Send a random chart image or a placeholder image for Swing Trade
        image_url = f"https://picsum.photos/600/400?random={random.randint(1, 1000)}"  # Random placeholder image
        await query.edit_message_text(
            text="Swing Trading focuses on taking advantage of short to medium-term price swings in the market. It’s about buying and holding securities for a few days to a few weeks.",
            reply_markup=back_button_markup,  # Include back button
        )
        await query.message.reply_photo(
            photo=image_url, reply_markup=back_button_markup
        )

    elif choice == "long_term":
        # Send a random chart image or a placeholder image for Long Term
        image_url = f"https://picsum.photos/600/400?random={random.randint(1, 1000)}"  # Random placeholder image
        await query.edit_message_text(
            text="Long Term Investing focuses on buying and holding securities for an extended period, typically several years. It's aimed at capital appreciation and dividends over time.",
            reply_markup=back_button_markup,  # Include back button
        )
        await query.message.reply_photo(
            photo=image_url, reply_markup=back_button_markup
        )

    elif choice == "download_mtf":
        await query.edit_message_text(
            "Fetching data and generating files... this may take a moment.",
            reply_markup=back_button_markup,
        )

        # 1. Fetch the data
        mtf_data = fetch_groww_mtf_data()

        if not mtf_data:
            await query.edit_message_text(
                "Could not fetch data. Please try again later.",
                reply_markup=back_button_markup,
            )
            return

        # 2. Split data based on leverage and save to files
        leverage_2_to_3 = [stock for stock in mtf_data if 2 <= stock["leverage"] <= 3]
        leverage_3_to_4 = [stock for stock in mtf_data if 3 <= stock["leverage"] <= 4]

        file_2_to_3 = "groww_mtf_leverage_2_to_3.csv"
        file_3_to_4 = "groww_mtf_leverage_3_to_4.csv"

        save_to_csv(leverage_2_to_3, file_2_to_3)
        save_to_csv(leverage_3_to_4, file_3_to_4)

        # 3. Send the files to the user
        try:
            await query.message.reply_document(document=open(file_2_to_3, "rb"))
            await query.message.reply_document(document=open(file_3_to_4, "rb"))
            await query.message.reply_text(
                "The files have been generated and sent!",
                reply_markup=back_button_markup,
            )
        except Exception as e:
            logger.error(f"Failed to send documents: {e}")
            await query.message.reply_text(
                "I'm sorry, there was an error sending the files. Please try again.",
                reply_markup=back_button_markup,
            )

        # 4. Clean up the local files
        import os

        if os.path.exists(file_2_to_3):
            os.remove(file_2_to_3)
        if os.path.exists(file_3_to_4):
            os.remove(file_3_to_4)

    elif choice == "back_to_menu":
        await back_to_menu(update, context)  # Return to the main menu


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages that are not commands or button presses."""
    await update.message.reply_text(
        "Sorry, I didn't understand that command. Please choose one of the options from the menu.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")]]
        ),  # Always have the Back button
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a list of options with inline buttons."""
    user = update.effective_user

    # Define inline buttons for the options
    keyboard = [
        [InlineKeyboardButton("Swing trade", callback_data="swing_trade")],
        [InlineKeyboardButton("Long Term", callback_data="long_term")],
        [InlineKeyboardButton("Download Grow MTF Data", callback_data="download_mtf")],
        [InlineKeyboardButton("Back to Menu", callback_data="back_to_menu")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with inline buttons (use query.message here for button responses)
    await update.callback_query.message.reply_text(  # Corrected to use callback_query.message
        f"Hi {user.full_name}!\n\nPlease choose an option:", reply_markup=reply_markup
    )


# ... (your imports and handler functions)

