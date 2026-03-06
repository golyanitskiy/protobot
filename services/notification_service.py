# services/notification_service.py
from aiogram import Bot
import logging
from config import ADMIN_BOT_TOKEN, ADMIN_ID, USER_BOT_TOKEN

logger = logging.getLogger(__name__)

admin_bot = Bot(token=ADMIN_BOT_TOKEN)
user_bot = Bot(token=USER_BOT_TOKEN)


async def notify_admin_about_complaint(
        user_id: int,
        username: str,
        link_url: str,
        link_id: int,
        complaints_count: int
):
    """Отправляет уведомление админу через admin-бота"""
    try:
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="🔴 Деактивировать ссылку",
            callback_data=f"deactivate_link:{link_id}"
        )

        await admin_bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"⚠️ *Новая жалоба на ссылку!*\n\n"
                f"Пользователь: @{username} (ID: {user_id})\n"
                f"Ссылка: {link_url}\n"
                f"ID ссылки: {link_id}\n"
                f"Всего жалоб на эту ссылку: {complaints_count}"
            ),
            parse_mode="Markdown",
            reply_markup=keyboard.as_markup()
        )
        logger.info(f"Notification sent to admin about complaint on link {link_id}")
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")


async def close_notification_bot():
    """Закрывает сессии обоих ботов"""
    try:
        await admin_bot.session.close()
        await user_bot.session.close()
        logger.info("Bots sessions closed")
    except Exception as e:
        logger.error(f"Error closing bots: {e}")


async def send_to_user_via_admin(user_id: int, text: str) -> bool:
    """Отправляет сообщение пользователю через admin-бота"""
    try:
        bot_info = await admin_bot.get_me()
        logger.info(f"Sending via admin-bot: @{bot_info.username} to user {user_id}")

        await admin_bot.send_message(user_id, text)
        logger.info(f"Successfully sent to user {user_id} via admin-bot")
        return True
    except Exception as e:
        logger.error(f"Failed to send to user {user_id} via admin-bot: {e}")
        return False


async def send_to_user_via_user_bot(user_id: int, text: str) -> bool:
    """Отправляет сообщение пользователю через user-бота"""
    try:
        bot_info = await user_bot.get_me()
        logger.info(f"Sending via user-bot: @{bot_info.username} to user {user_id}")

        await user_bot.send_message(user_id, text)
        logger.info(f"Successfully sent to user {user_id} via user-bot")
        return True
    except Exception as e:
        logger.error(f"Failed to send to user {user_id} via user-bot: {e}")
        return False


# Универсальная функция (пытается отправить через user-бота, если не получается - через admin-бота)
async def send_to_user(user_id: int, text: str) -> bool:
    """Пытается отправить через user-бота, затем через admin-бота"""
    # Сначала пробуем через user-бота (предпочтительный способ)
    success = await send_to_user_via_user_bot(user_id, text)
    if success:
        return True

    # Если не вышло, пробуем через admin-бота
    logger.warning(f"User-bot failed for {user_id}, trying admin-bot")
    return await send_to_user_via_admin(user_id, text)