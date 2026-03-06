# user_bot/handlers/links.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
import logging

from services.link_service import get_current_active_link, increment_complaints
from services.notification_service import notify_admin_about_complaint  # Это имя правильное

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "report_broken_link")
async def report_broken_link(callback: CallbackQuery):
    """Обработчик кнопки 'Ссылка не работает'"""
    user_id = callback.from_user.id
    username = callback.from_user.username or "нет username"

    # Получаем текущую активную ссылку
    current_link = get_current_active_link()
    if not current_link:
        await callback.message.edit_text("❌ Сейчас нет активной ссылки.")
        await callback.answer()
        return

    # Увеличиваем счетчик жалоб (НО НЕ деактивируем ссылку)
    new_count = increment_complaints(current_link['id'])

    # Сообщение пользователю
    await callback.message.edit_text(
        "✅ Спасибо! Ваша жалоба отправлена администратору."
    )

    # Отправляем уведомление админу
    await notify_admin_about_complaint(
        user_id=user_id,
        username=username,
        link_url=current_link['url'],
        link_id=current_link['id'],
        complaints_count=new_count
    )

    await callback.answer()
    logger.info(f"Complaint on link {current_link['id']} from user {user_id}, total: {new_count}")