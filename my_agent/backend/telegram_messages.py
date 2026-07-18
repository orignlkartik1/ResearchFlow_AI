import logging
import os
import tempfile
from collections.abc import Awaitable, Callable
from typing import Any

from telegram import Message
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4000
ATTACHMENT_THRESHOLD = 100000000


def split_telegram_message(text: str, max_length: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split Telegram text while preferring paragraph boundaries."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""

    for index, paragraph in enumerate(text.split("\n\n")):
        part = paragraph if index == 0 else f"\n\n{paragraph}"

        if len(part) > max_length:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_oversized_part(part, max_length))
            continue

        if len(current) + len(part) <= max_length:
            current += part
        else:
            if current:
                chunks.append(current)
            current = part.lstrip("\n")

    if current:
        chunks.append(current)

    return chunks


def _split_oversized_part(text: str, max_length: int) -> list[str]:
    chunks: list[str] = []
    remaining = text

    while len(remaining) > max_length:
        split_at = _find_safe_split_index(remaining, max_length)
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    if remaining:
        chunks.append(remaining)

    return chunks


def _find_safe_split_index(text: str, max_length: int) -> int:
    for separator in ("\n", " "):
        index = text.rfind(separator, 0, max_length + 1)
        if index > 0:
            return index
    return max_length


async def send_long_message(bot: Any, chat_id: int | str, text: str, **kwargs: Any) -> list[Message]:
    """
    Send text through Telegram without exceeding the sendMessage length limit.

    Very large responses are attached as a UTF-8 text file because many chunks are
    hard to read in chat and are more likely to hit rate/API edge cases.
    """
    text = str(text)

    if len(text) > ATTACHMENT_THRESHOLD:
        return await _send_text_file(bot, chat_id, text, **kwargs)

    sent_messages: list[Message] = []
    for chunk in split_telegram_message(text):
        try:
            sent_messages.append(
                await bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    **kwargs,
                )
            )
        except TelegramError:
            logger.exception("Telegram API error while sending message chunk")
            continue
        except Exception:
            logger.exception("Unexpected error while sending message chunk")
            continue

    return sent_messages


async def reply_long_text(message: Message, text: str, **kwargs: Any) -> list[Message]:
    return await send_long_message(
        message.get_bot(),
        message.chat_id,
        text,
        **kwargs,
    )


async def _send_text_file(bot: Any, chat_id: int | str, text: str, **kwargs: Any) -> list[Message]:
    sent_messages: list[Message] = []
    temp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".txt",
            prefix="researchflow_response_",
            delete=False,
        ) as temp_file:
            temp_file.write(text)
            temp_path = temp_file.name

        sent_messages.extend(
            await send_long_message(
                bot,
                chat_id,
                "The response is too long to display in Telegram. I've attached the complete output.",
                **kwargs,
            )
        )

        try:
            with open(temp_path, "rb") as document:
                sent_messages.append(
                    await bot.send_document(
                        chat_id=chat_id,
                        document=document,
                        filename="researchflow_response.txt",
                    )
                )
        except TelegramError:
            logger.exception("Telegram API error while sending long response document")
        except Exception:
            logger.exception("Unexpected error while sending long response document")

    except Exception:
        logger.exception("Failed to create or send long response document")
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                logger.exception("Failed to delete temporary response file: %s", temp_path)

    return sent_messages


async def safe_delete_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramError:
        logger.exception("Telegram API error while deleting message")
    except Exception:
        logger.exception("Unexpected error while deleting message")


async def safe_edit_text(
    edit_call: Callable[..., Awaitable[Message]],
    text: str,
    **kwargs: Any,
) -> Message | None:
    try:
        return await edit_call(text, **kwargs)
    except TelegramError:
        logger.exception("Telegram API error while editing message")
    except Exception:
        logger.exception("Unexpected error while editing message")
    return None
