# admin_bot/handlers/links.py
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from common_services.access_service import get_active_users
from services.link_service import add_link, get_current_active_link

router = Router()
logger = logging.getLogger(__name__)


# 🔹 FSM состояния для добавления ссылки
class AddLinkState(StatesGroup):
    waiting_for_url = State()


# 🔹 Команда /add_link
@router.message(F.text == "/add_link")
async def add_link_start(message: Message, state: FSMContext):
    """Начало процесса добавления ссылки"""
    await message.answer("Отправьте ссылку (должна начинаться с tg://)")
    await state.set_state(AddLinkState.waiting_for_url)


# 🔹 Обработка ссылки
@router.message(AddLinkState.waiting_for_url)
async def add_link_process(message: Message, state: FSMContext):
    """Обработка полученной ссылки и рассылка"""
    url = message.text.strip()

    # Проверяем корректность ссылки
    if not url.startswith("tg://"):
        await message.answer(
            "❌ Некорректная ссылка. Должна начинаться с tg://\n"
            "Попробуйте ещё раз или отправьте /cancel"
        )
        return

    try:
        # Добавляем ссылку (она автоматически становится активной)
        link_id = add_link(url)
        logger.info(f"Admin added new link ID {link_id}: {url}")

        # Получаем активных пользователей
        users = get_active_users()

        if not users:
            await message.answer("✅ Ссылка добавлена, но нет активных пользователей для рассылки.")
            await state.clear()
            return

        # Рассылаем всем активным пользователям
        sent_count = 0
        for user in users:
            try:
                # Создаем клавиатуру со ссылкой
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔗 Перейти по ссылке", url=url)]
                    ]
                )

                await message.bot.send_message(
                    user["user_id"],
                    "📌 *Новая ссылка доступна!*",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send to user {user['user_id']}: {e}")

        # Отправляем отчет админу
        await message.answer(
            f"✅ Ссылка добавлена и отправлена {sent_count} пользователям."
        )

    except Exception as e:
        logger.error(f"Error in add_link_process: {e}")
        await message.answer("❌ Произошла ошибка при добавлении ссылки.")

    await state.clear()


# 🔹 Команда /links — показать текущую активную ссылку
@router.message(F.text == "/links")
async def show_active_link(message: Message):
    """Показывает текущую активную ссылку"""
    try:
        link = get_current_active_link()

        if not link:
            await message.answer("🔍 В данный момент нет активной ссылки.")
            return

        # Создаем клавиатуру со ссылкой для админа
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Перейти по ссылке", url=link['url'])]
            ]
        )

        await message.answer(
            f"🔗 *Текущая активная ссылка:*\n"
            f"`{link['url']}`\n\n"
            f"📅 Добавлена: {link['created_at']}\n"
            f"⚠️ Жалоб: {link.get('complaints_count', 0)}",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in show_active_link: {e}")
        await message.answer("❌ Ошибка при получении активной ссылки.")


# 🔹 Команда /cancel для отмены FSM
@router.message(F.text == "/cancel")
async def cancel_handler(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("🤷 Нет активного действия для отмены.")
        return

    await state.clear()
    await message.answer("✅ Действие отменено.")