from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Dispatcher, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.ext import ApplicationBuilder
from groww_mtf import generate_mtf_csv_files
from chart_generator import generate_chart
import os

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=1)

def back_to_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]])

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
        await query.edit_message_text(chart, reply_markup=back_to_menu())
    elif query.data == "longterm":
        chart = generate_chart("Long Term")
        await query.edit_message_text(chart, reply_markup=back_to_menu())
    elif query.data == "download":
        files = generate_mtf_csv_files()
        await query.edit_message_text("Here are your Groww MTF files:", reply_markup=back_to_menu())
        for file in files:
            await bot.send_document(chat_id=query.message.chat_id, document=open(file, "rb"))
    elif query.data == "back":
        await start(update, context)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(handle_button))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"