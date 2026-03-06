# services/scheduler_service.py
import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID, ADMIN_BOT_TOKEN
from services.link_service import get_expiring_links

logger = logging.getLogger(__name__)

admin_bot = Bot(token=ADMIN_BOT_TOKEN)


async def check_expiring_links():
    """Проверяет ссылки, которые истекают через 1 день"""
    while True:
        try:
            # Проверяем каждые 6 часов
            await asyncio.sleep(21600)  # 6 часов

            expiring_links = get_expiring_links(days_before=1)

            for link in expiring_links:
                # Создаем клавиатуру с действиями
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="🔴 Деактивировать сейчас",
                            callback_data=f"deactivate_expiring:{link['id']}"
                        )],
                        [InlineKeyboardButton(
                            text="➕ Добавить новую ссылку",
                            callback_data="add_new_link"
                        )]
                    ]
                )

                await admin_bot.send_message(
                    ADMIN_ID,
                    f"⚠️ *Внимание! Ссылка истекает через 1 день*\n\n"
                    f"🔗 ID: {link['id']}\n"
                    f"📅 Создана: {link['created_at']}\n"
                    f"⏰ Истекает: {link['expires_at']}\n"
                    f"📊 Жалоб: {link['complaints_count']}\n\n"
                    f"Рекомендуется подготовить новую ссылку.",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )

        except Exception as e:
            logger.error(f"Error in check_expiring_links: {e}")


async def start_scheduler():
    """Запускает планировщик"""
    asyncio.create_task(check_expiring_links())
    logger.info("Scheduler started")