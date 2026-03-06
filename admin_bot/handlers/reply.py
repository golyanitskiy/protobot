# admin_bot/handlers/reply.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging
import re

from config import ADMIN_ID
from services.notification_service import user_bot

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("reply"))
async def reply_to_user(message: Message):
    """Ответ пользователю: /reply <user_id> <текст>"""
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.strip()
    pattern = r'^/reply\s+(\d+)\s+(.+)$'
    match = re.match(pattern, text, re.DOTALL)

    if not match:
        await message.answer(
            "❌ *Неверный формат*\n\n"
            "Используйте: `/reply <user_id> <текст>`\n"
            "Пример: `/reply 123456789 Спасибо за обращение!`",
            parse_mode="Markdown"
        )
        return

    user_id = int(match.group(1))
    reply_text = match.group(2)

    try:
        # Отправляем ответ через user-бота
        await user_bot.send_message(
            chat_id=user_id,
            text=(
                f"📬 *Ответ от администратора*\n\n"
                f"{reply_text}"
            ),
            parse_mode="Markdown"
        )

        await message.answer(
            f"✅ *Ответ отправлен пользователю {user_id}*",
            parse_mode="Markdown"
        )
        logger.info(f"Admin replied to user {user_id}")

    except Exception as e:
        logger.error(f"Failed to reply to user {user_id}: {e}")
        await message.answer(
            f"❌ *Ошибка при отправке ответа*\n"
            f"Пользователь {user_id} недоступен.",
            parse_mode="Markdown"
        )