# user_bot/handlers/start.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
import logging

from config import ADMIN_ID
from services.access_service import is_access_active, grant_test_access
from services.link_service import add_link, has_active_link

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("test_send_user"))
async def test_send_user(message: Message):
    """Тестовая отправка (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /test_send_user <user_id>")
        return

    try:
        user_id = int(args[1])

        await message.bot.send_message(
            user_id,
            "🔔 Тестовое сообщение от user-бота"
        )
        await message.answer(f"✅ Отправлено через user-бота")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(CommandStart())
async def start_handler(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id

    try:
        if is_access_active(user_id):
            from services.link_service import get_current_active_link
            from user_bot.keyboards.inline import link_keyboard

            link = get_current_active_link()

            if link:
                # Отправляем ссылку с кнопкой жалобы
                await message.answer(
                    f"✅ *Ваш доступ активен!*\n\n"
                    f"📎 Ссылка:\n{link['url']}",
                    parse_mode="Markdown",
                    reply_markup=link_keyboard()
                )
                logger.info(f"Sent active link to user {user_id}")
            else:
                # Нет активной ссылки, но доступ есть
                await message.answer(
                    "✅ *Ваш доступ активен!*\n\n"
                    "⚠️ В данный момент нет активной ссылки.\n"
                    "Администратор уже уведомлён, ожидайте.",
                    parse_mode="Markdown"
                )
        else:
            # Доступ неактивен
            from user_bot.keyboards.inline import buy_keyboard
            await message.answer(
                "❌ *У вас нет активного доступа*\n\n"
                "💰 Оплатите 150 Stars для доступа на 30 дней.",
                parse_mode="Markdown",
                reply_markup=buy_keyboard()
            )

    except Exception as e:
        logger.error(f"Error in start_handler for user {user_id}: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(Command(commands=["test_access"]))
async def test_access(message: Message):
    """Тестовая команда для локального тестирования без оплаты"""
    user_id = message.from_user.id
    username = message.from_user.username or ""

    try:
        # Создаём тестовую ссылку, если её ещё нет
        if not has_active_link():
            # Добавляем ссылку (она добавляется с active=0)
            link_id = add_link("https://example.com/test-link")
            logger.info(f"Created test link with ID {link_id}")

            # активируем её
            from services.link_service import activate_link
            activate_link(link_id)
            logger.info(f"Activated test link {link_id}")

        # Активируем доступ пользователя
        if grant_test_access(user_id, username):
            # Отправляем ссылку пользователю
            from services.link_service import get_current_active_link
            link = get_current_active_link()

            if link:
                await message.answer(
                    f"✅ *Тестовый доступ активирован!*\n\n"
                    f"📌 Ссылка:\n{link['url']}",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    "✅ Тестовый доступ активирован!\n"
                    "Но активной ссылки нет. Обратитесь к администратору."
                )
        else:
            await message.answer("❌ Ошибка при активации тестового доступа.")

    except Exception as e:
        logger.error(f"Error in test_access for user {user_id}: {e}")
        await message.answer("❌ Произошла ошибка.")