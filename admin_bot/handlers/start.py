# admin_bot/handlers/start.py
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMIN_ID
from services.link_service import add_link
from services.access_service import get_active_users
from services.notification_service import send_to_user_via_user_bot

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "/start")
async def start_handler(message: Message):
    """Обработчик команды /start"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    await message.answer(
        "👋 Привет, админ!\n\n"
        "Используйте команды:\n"
        "/add_link — добавить новую ссылку\n"
        "/links — показать активные ссылки\n"
        "/reply <user_id> <текст> — ответить пользователю"
    )


# Состояния для добавления ссылки
class AddLinkState(StatesGroup):
    waiting_for_url = State()


# 🔹 Команда /add_link — запускаем FSM
@router.message(F.text == "/add_link")
async def add_link_start(message: Message, state: FSMContext):
    """Начало процесса добавления ссылки"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    await message.answer("Отправьте ссылку для рассылки всем активным пользователям (должна начинаться с tg://):")
    await state.set_state(AddLinkState.waiting_for_url)


# 🔹 Обработка текста со ссылкой
@router.message(AddLinkState.waiting_for_url)
async def add_link_process(message: Message, state: FSMContext):
    """Обработка полученной ссылки и рассылка через user-бота"""
    url = message.text.strip()

    # Проверка на tg://
    if not url.startswith("tg://"):
        await message.answer("❌ Некорректная ссылка. Отправьте ссылку, начинающуюся с tg://")
        return

    try:
        # Добавляем ссылку в БД
        add_link(url)
        logger.info(f"Admin added new link: {url}")

        # Получаем активных пользователей
        users = get_active_users()

        if not users:
            await message.answer("✅ Ссылка добавлена в БД, но нет активных пользователей для рассылки.")
            await state.clear()
            return

        # Рассылка всем пользователям через user-бота
        sent_count = 0
        failed_count = 0
        failed_users = []

        for user in users:
            try:
                # Получаем ID пользователя
                user_id = user.get('user_id') or user.get('id')

                if not user_id:
                    logger.error(f"Invalid user object (no user_id): {user}")
                    failed_count += 1
                    continue

                # Отправляем через user-бота
                success = await send_to_user_via_user_bot(user_id, url)

                if success:
                    sent_count += 1
                    logger.info(f"Successfully sent to user {user_id}")
                else:
                    failed_count += 1
                    failed_users.append(str(user_id))
                    logger.warning(f"Failed to send to user {user_id} via user-bot")

            except Exception as e:
                failed_count += 1
                user_id = user.get('user_id', 'unknown')
                failed_users.append(str(user_id))
                logger.error(f"Exception sending to user {user_id}: {e}")

        # Отправляем отчет админу
        report = f"✅ Ссылка добавлена.\n"
        report += f"📤 Отправлено: {sent_count} пользователям\n"

        if failed_count > 0:
            report += f"❌ Не удалось отправить: {failed_count} пользователям\n"
            if failed_users:
                report += f"👤 ID: {', '.join(failed_users[:3])}"
                if len(failed_users) > 3:
                    report += f" и ещё {len(failed_users) - 3}"

        await message.answer(report)

    except Exception as e:
        logger.error(f"Error in add_link_process: {e}")
        await message.answer("❌ Произошла ошибка при добавлении ссылки.")

    await state.clear()


# 🔹 Команда /cancel для отмены FSM
@router.message(F.text == "/cancel")
async def cancel_handler(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    if message.from_user.id != ADMIN_ID:
        return

    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    await state.clear()
    await message.answer("✅ Действие отменено.")


# 🔹 Команда для тестирования отправки
@router.message(F.text.startswith("/test_send"))
async def test_send_command(message: Message):
    """Тестовая отправка сообщения пользователю через user-бота"""
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /test_send <user_id>")
        return

    try:
        user_id = int(args[1])

        # Используем ту же функцию, что и для рассылки
        from services.notification_service import send_to_user_via_user_bot

        success = await send_to_user_via_user_bot(
            user_id,
            "tg://test?message=Тестовое сообщение"
        )

        if success:
            await message.answer(f"✅ Сообщение успешно отправлено пользователю {user_id}")
        else:
            await message.answer(f"❌ Не удалось отправить сообщение пользователю {user_id}")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")