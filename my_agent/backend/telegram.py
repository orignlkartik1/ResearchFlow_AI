import httpx

from my_agent.env import require_env

require_env("GOOGLE_API_KEY")

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

BOT_TOKEN = require_env("TELEGRAM_TOKEN")

API = "http://127.0.0.1:8000/chat"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I am ResearchFlow AI."
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = {
        "user_id": str(update.effective_user.id),
        "message": update.message.text,
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(API, json=payload)

    await update.message.reply_text(
        r.json()["response"]
    )


app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        chat,
        )
)

app.run_polling()
