import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Define a token for your bot. Replace 'YOUR_BOT_TOKEN' with your actual bot token.
# You can get this from BotFather on Telegram.
BOT_TOKEN = '7642750843:AAF16-J7GXCeSI85-D67y29_es3IhYdCoic'

# --- Handlers for the commands and messages ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and a main menu with options."""
    # Define the keyboard layout
    keyboard = [['Swing trade'], ['Long Term']]

    # Create the ReplyKeyboardMarkup
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.full_name}!\nWelcome to the trading bot. Please select an option:",
        reply_markup=reply_markup
    )

async def swing_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message and an image for the 'Swing trade' option."""
    # The URL for a swing trading image.
    # Replace this with your preferred image URL.
    image_url = 'https://picsum.photos/600/400'
    
    # Create a "Back to Menu" button
    keyboard = [['Back to Menu']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    # Send the image with a caption
    await update.message.reply_photo(
        photo=image_url,
        caption="Here's some information on Swing Trading. It focuses on taking advantage of short to medium-term price swings in the market.",
        reply_markup=reply_markup
    )

async def long_term(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message for the 'Long Term' option."""
    # Create a "Back to Menu" button
    keyboard = [['Back to Menu']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "The 'Long Term' feature is under development. Stay tuned for more updates!",
        reply_markup=reply_markup
    )

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Back to Menu' button click by calling the start function."""
    await start(update, context)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages that are not commands or button presses."""
    await update.message.reply_text(
        "Sorry, I didn't understand that command. Please use the menu or /start to begin."
    )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - add handlers
    application.add_handler(CommandHandler("start", start))

    # on non-command i.e Message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.Regex('^Swing trade$'), swing_trade))
    application.add_handler(MessageHandler(filters.Regex('^Long Term$'), long_term))
    application.add_handler(MessageHandler(filters.Regex('^Back to Menu$'), back_to_menu))
    
    # Handle unknown messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT.
    application.run_polling()


if __name__ == '__main__':
    main()
