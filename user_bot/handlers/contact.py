# user_bot/handlers/contact.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMIN_ID
from services.notification_service import admin_bot
from user_bot.keyboards.inline import cancel_keyboard

router = Router()
logger = logging.getLogger(__name__)


# Состояния для обращения к админу
class ContactState(StatesGroup):
    waiting_for_message = State()


@router.callback_query(F.data == "contact_admin")
async def contact_admin_start(callback: CallbackQuery, state: FSMContext):
    """Начало обращения к админу"""
    await callback.message.edit_text(
        "📝 *Напишите ваше сообщение администратору*\n\n"
        "Опишите проблему или задайте вопрос. Администратор ответит вам в ближайшее время.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(ContactState.waiting_for_message)
    await callback.answer()


@router.message(ContactState.waiting_for_message)
async def process_contact_message(message: Message, state: FSMContext):
    """Обработка сообщения для админа"""
    user_id = message.from_user.id
    username = message.from_user.username or "нет username"
    user_text = message.text

    # Отправляем админу
    try:
        await admin_bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📬 *Новое обращение от пользователя*\n\n"
                f"👤 ID: {user_id}\n"
                f"👤 Username: @{username}\n"
                f"💬 Сообщение:\n{user_text}"
            ),
            parse_mode="Markdown"
        )

        await message.answer(
            "✅ *Сообщение отправлено администратору!*\n\n"
            "Ожидайте ответа. Спасибо за обращение!",
            parse_mode="Markdown"
        )
        logger.info(f"Contact message from user {user_id} sent to admin")

    except Exception as e:
        logger.error(f"Failed to send contact to admin: {e}")
        await message.answer(
            "❌ *Ошибка при отправке сообщения*\n\n"
            "Попробуйте позже или напишите напрямую.",
            parse_mode="Markdown"
        )

    await state.clear()


@router.callback_query(F.data == "cancel_contact")
async def cancel_contact(callback: CallbackQuery, state: FSMContext):
    """Отмена обращения"""
    await state.clear()
    await callback.message.edit_text("❌ Обращение отменено.")
    await callback.answer()