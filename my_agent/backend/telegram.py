import logging

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from my_agent.env import require_env

# --------------------------------------------------------------------
# Environment Variables
# --------------------------------------------------------------------

BOT_TOKEN = require_env("TELEGRAM_TOKEN")

# Change this after deployment
API = "http://127.0.0.1:8000/chat"

# --------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# HTTP Timeout
# --------------------------------------------------------------------

TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=300.0,      # Wait up to 5 minutes for the AI response
    write=30.0,
    pool=10.0,
)

# --------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to ResearchFlow AI!\n\n"
        "I can help you analyze research papers, discover recent work, "
        "and suggest future research directions.\n\n"
        "Send me a message to begin."
    )


# --------------------------------------------------------------------
# Chat Handler
# --------------------------------------------------------------------


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.effective_user.id)
    message = update.message.text

    logger.info("Message received from %s", user_id)

    # Show typing animation
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    # Inform the user
    processing_msg = await update.message.reply_text(
        "📄 Request received.\n\n"
        "🔍 ResearchFlow AI is analyzing your request.\n"
        "⏳ Please wait..."
    )

    payload = {
        "user_id": user_id,
        "message": message,
    }

    try:

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:

            response = await client.post(
                API,
                json=payload,
            )

        response.raise_for_status()

        data = response.json()

        reply = data.get(
            "response",
            "Sorry, I couldn't generate a response.",
        )

        await processing_msg.edit_text(reply)

    except httpx.ReadTimeout:

        logger.exception("Backend timeout")

        await processing_msg.edit_text(
            "⏳ The analysis is taking longer than expected.\n\n"
            "Please try again in a few moments."
        )

    except httpx.ConnectError:

        logger.exception("Cannot connect to backend")

        await processing_msg.edit_text(
            "❌ Unable to connect to ResearchFlow AI backend.\n\n"
            "Please try again later."
        )

    except httpx.HTTPStatusError as e:

        logger.exception("HTTP Error")

        await processing_msg.edit_text(
            f"⚠️ Backend returned an error.\n\n"
            f"Status Code: {e.response.status_code}"
        )

    except Exception as e:

        logger.exception("Unexpected Error")

        await processing_msg.edit_text(
            "❌ An unexpected error occurred.\n\n"
            f"{str(e)}"
        )


# --------------------------------------------------------------------
# Telegram Application
# --------------------------------------------------------------------

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        chat,
        )
)

logger.info("ResearchFlow AI Telegram Bot Started")

app.run_polling()
