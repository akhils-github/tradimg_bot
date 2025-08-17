from threading import Thread
import asyncio
from waitress import serve
from bot import app, application
import os

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def start_bot():
        await application.initialize()
        await application.start()
        await application.updater.start_polling()

    loop.run_until_complete(start_bot())

if __name__ == "__main__":
    Thread(target=run_bot).start()

    port = int(os.environ.get("PORT", 5000))
    serve(app, host="0.0.0.0", port=port)
