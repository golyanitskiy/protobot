# admin_bot/handlers/links_handler.py
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMIN_ID
from datetime import datetime
from services.access_service import get_active_users
from services.link_service import deactivate_link, add_link

router = Router()
logger = logging.getLogger(__name__)


# FSM состояние для добавления ссылки после деактивации
class AddLinkAfterDeactivation(StatesGroup):
    waiting_for_url = State()


# FSM состояние для добавления ссылки
class AddLinkState(StatesGroup):
    waiting_for_url = State()


@router.message(Command("test_send"))
async def test_send_to_user(message: Message):
    """Тестовая отправка сообщения пользователю через user-бота"""
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /test_send <user_id>")
        return

    try:
        user_id = int(args[1])

        # Отправляем через user-бота
        from aiogram import Bot
        from config import USER_BOT_TOKEN
        user_bot = Bot(token=USER_BOT_TOKEN)

        await user_bot.send_message(
            user_id,
            "🔔 Тестовое сообщение от администратора (через user-бота)."
        )
        await user_bot.session.close()

        await message.answer(f"✅ Сообщение успешно отправлено пользователю {user_id} через user-бота")

    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")


@router.message(Command("test_users"))
async def test_users_command(message: Message):
    """Диагностика: показывает всех пользователей в БД"""
    if message.from_user.id != ADMIN_ID:
        return

    try:
        from database.db import get_connection

        with get_connection() as conn:
            cursor = conn.cursor()

            # Все пользователи
            cursor.execute("SELECT user_id, username, access_until FROM users")
            all_users = cursor.fetchall()

            # Активные пользователи
            cursor.execute("SELECT user_id, username, access_until FROM users WHERE access_until > datetime('now')")
            active_users = cursor.fetchall()

            report = "📊 *Диагностика пользователей:*\n\n"
            report += f"📝 Всего в БД: {len(all_users)}\n"
            report += f"✅ Активных: {len(active_users)}\n\n"

            if all_users:
                report += "*Все пользователи:*\n"
                for user in all_users:
                    status = "✅" if user['access_until'] and user['access_until'] > datetime.now().isoformat() else "❌"
                    report += f"{status} ID: {user['user_id']}, @{user['username']}, доступ до: {user['access_until']}\n"

            await message.answer(report[:4000], parse_mode="Markdown")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.callback_query(F.data.startswith("deactivate_link:"))
async def process_deactivate_link(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия админом кнопки деактивации ссылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    # Логируем, какой бот получил callback
    bot_info = await callback.bot.get_me()
    logger.info(f"Callback received by bot: @{bot_info.username}")

    # Разбираем данные: deactivate_link:link_id
    _, link_id_str = callback.data.split(':')
    link_id = int(link_id_str)

    # Деактивируем ссылку
    success = deactivate_link(link_id)
    if not success:
        await callback.message.edit_text("❌ Не удалось деактивировать ссылку.")
        await callback.answer()
        return

    # Обновляем сообщение с уведомлением
    await callback.message.edit_text(
        f"✅ Ссылка #{link_id} деактивирована.\n\n"
        f"📝 Отправьте новую ссылку для рассылки пользователям:"
    )

    # УСТАНАВЛИВАЕМ СОСТОЯНИЕ FSM
    await state.set_state(AddLinkAfterDeactivation.waiting_for_url)
    logger.info(f"✅ State set to: {await state.get_state()}")

    # Получаем активных пользователей
    users = get_active_users()
    logger.info(f"Active users: {[u['user_id'] for u in users]}")

    sent = 0
    failed = 0
    failed_users = []

    # Импортируем user-бота для отправки пользователям
    from aiogram import Bot
    from config import USER_BOT_TOKEN
    user_bot = Bot(token=USER_BOT_TOKEN)

    try:
        for user in users:
            try:
                # Отправляем через user-бота
                await user_bot.send_message(
                    user['user_id'],
                    "🔔Ссылка деактивирована. Ожидайте новую ссылку."
                )
                sent += 1
                logger.info(f"Successfully notified user {user['user_id']} via user-bot")
            except Exception as e:
                failed += 1
                failed_users.append(str(user['user_id']))
                logger.error(f"Failed to notify user {user['user_id']} via user-bot: {e}")
    finally:
        # Закрываем сессию ПОСЛЕ цикла
        await user_bot.session.close()

    # Логируем статистику
    if failed_users:
        logger.info(f"Failed to notify {len(failed_users)} users: {', '.join(failed_users)}")

    logger.info(f"Deactivation notification: sent to {sent}, failed {failed}")

    await callback.answer()


@router.callback_query(F.data.startswith("activate_link:"))
async def process_activate_link(callback: CallbackQuery):
    """Активация ссылки и рассылка пользователям"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    _, link_id_str = callback.data.split(':')
    link_id = int(link_id_str)

    # Получаем информацию о ссылке до активации
    from services.link_service import get_link_by_id
    link = get_link_by_id(link_id)

    if not link:
        await callback.message.edit_text("❌ Ссылка не найдена")
        await callback.answer()
        return

    # Активируем ссылку
    from services.link_service import activate_link
    success = activate_link(link_id)

    if success:
        # Получаем активных пользователей
        from services.access_service import get_active_users
        users = get_active_users()

        # Рассылаем новую ссылку
        sent_count = 0
        for user in users:
            try:
                from aiogram import Bot
                from config import USER_BOT_TOKEN
                user_bot = Bot(token=USER_BOT_TOKEN)

                await user_bot.send_message(
                    user['user_id'],
                    f"📌 *Новая ссылка доступна!*\n\n{link['url']}",
                    parse_mode="Markdown"
                )
                await user_bot.session.close()
                sent_count += 1

            except Exception as e:
                logger.error(f"Failed to send to user {user['user_id']}: {e}")

        await callback.message.edit_text(
            f"✅ Ссылка #{link_id} активирована!\n"
            f"📤 Отправлена {sent_count} пользователям"
        )

    else:
        await callback.message.edit_text(
            f"❌ Не удалось активировать ссылку #{link_id}"
        )

    await callback.answer()


@router.message(AddLinkAfterDeactivation.waiting_for_url)
async def process_new_link_after_deactivation(message: Message, state: FSMContext):
    """Обработка новой ссылки после деактивации"""
    if message.from_user.id != ADMIN_ID:
        return

    logger.info(f"🔥 process_new_link_after_deactivation вызвана с сообщением: {message.text}")

    url = message.text.strip()

    # Проверяем корректность ссылки
    if not url.startswith("tg://"):
        await message.answer(
            "❌ Некорректная ссылка. Должна начинаться с tg://\n"
            "Попробуйте ещё раз или отправьте /cancel"
        )
        return

    try:
        # Добавляем новую ссылку
        link_id = add_link(url)
        logger.info(f"Admin added new link ID {link_id}: {url}")

        # Получаем активных пользователей
        users = get_active_users()
        logger.info(f"Found {len(users)} active users: {[u['user_id'] for u in users]}")

        if not users:
            await message.answer("✅ Ссылка добавлена, но нет активных пользователей для рассылки.")
            await state.clear()
            return

        # Рассылаем новую ссылку через user-бота
        sent_count = 0
        failed_count = 0
        failed_users = []

        # Импортируем функцию для отправки
        from services.notification_service import send_to_user_via_user_bot

        for user in users:
            current_user_id = user.get('user_id')  # Определяем переменную в начале цикла
            try:
                if not current_user_id:
                    logger.error(f"Invalid user object: {user}")
                    failed_count += 1
                    failed_users.append("unknown")
                    continue

                # Отправляем через user-бота (используем готовую функцию)
                success = await send_to_user_via_user_bot(
                    current_user_id,
                    f"📌 Новая ссылка:\n{url}"
                )

                if success:
                    sent_count += 1
                    logger.info(f"Successfully sent to user {current_user_id} via user-bot")
                else:
                    failed_count += 1
                    failed_users.append(str(current_user_id))
                    logger.warning(f"Failed to send to user {current_user_id}")

            except Exception as e:
                failed_count += 1
                user_id_str = str(current_user_id) if current_user_id else "unknown"
                failed_users.append(user_id_str)
                logger.error(f"Exception sending to user {current_user_id}: {e}")

        # Формируем отчет для админа
        report = f"✅ *Новая ссылка добавлена*\n\n"
        report += f"📤 Отправлено: {sent_count} из {len(users)} пользователей\n"
        report += f"👤 Получатели: {', '.join([str(u['user_id']) for u in users])}\n"

        if failed_count > 0:
            report += f"❌ Не удалось отправить: {failed_count} пользователям\n"
            if failed_users:
                report += f"👤 Проблемные ID: {', '.join(failed_users[:3])}"
                if len(failed_users) > 3:
                    report += f" и ещё {len(failed_users) - 3}"

        await message.answer(report, parse_mode="Markdown")

        logger.info(f"Broadcast stats: sent {sent_count}, failed {failed_count}")

    except Exception as e:
        logger.error(f"Error adding new link: {e}")
        await message.answer("❌ Произошла ошибка при добавлении ссылки.")

    await state.clear()


@router.message(Command("links"))
async def show_links_command(message: Message):
    """Команда /links для просмотра активной ссылки"""
    if message.from_user.id != ADMIN_ID:
        return

    from services.link_service import get_all_active_links
    links = get_all_active_links()

    # ОТЛАДКА
    logger.info(f"LINKS DEBUG: get_all_active_links() вернула {len(links)} ссылок")
    for link in links:
        logger.info(f"LINKS DEBUG: link = {dict(link)}")

    if not links:
        await message.answer("🔍 Нет активных ссылок.")
        return

    for link in links:
        # Проверяем, что есть все нужные поля
        link_id = link.get('id')
        url = link.get('url', 'No URL')
        created_at = link.get('created_at', 'Unknown')
        expires_at = link.get('expires_at', 'Unknown')
        complaints = link.get('complaints_count', 0)

        logger.info(f"LINKS DEBUG: создаем кнопку для ссылки ID {link_id}")

        # Создаем клавиатуру для каждой ссылки
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔴 Деактивировать ссылку",
                    callback_data=f"deactivate_link:{link_id}"
                )]
            ]
        )

        await message.answer(
            f"🔗 *Активная ссылка:*\n"
            f"{url}\n\n"
            f"🆔 ID: {link_id}\n"
            f"📅 Добавлена: {created_at}\n"
            f"⏰ Истекает: {expires_at}\n"
            f"⚠️ Жалоб: {complaints}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        logger.info(f"LINKS DEBUG: сообщение отправлено с кнопкой для ссылки {link_id}")


# Команда для отмены
@router.message(Command("cancel"))
async def cancel_add_link(message: Message, state: FSMContext):
    """Отмена добавления ссылки"""
    if message.from_user.id != ADMIN_ID:
        return

    current_state = await state.get_state()
    if current_state is None:
        await message.answer("🤷 Нет активного действия для отмены.")
        return

    await state.clear()
    await message.answer("✅ Добавление ссылки отменено.")


@router.message(Command("test_both_bots"))
async def test_both_bots(message: Message):
    """Тестирует отправку через обоих ботов"""
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /test_both_bots <user_id>")
        return

    try:
        user_id = int(args[1])
        report = f"🔍 *Тестирование отправки пользователю {user_id}*\n\n"

        # Тест через admin-бота
        try:
            from services.notification_service import admin_bot  # Исправлено: notification_bot -> admin_bot
            await admin_bot.send_chat_action(user_id, action="typing")
            report += "✅ admin-бот: пользователь доступен\n"
        except Exception as e:
            report += f"❌ admin-бот: {str(e)[:100]}\n"

        # Тест через user-бота
        try:
            from services.notification_service import user_bot  # Исправлено: используем существующий user_bot
            await user_bot.send_chat_action(user_id, action="typing")
            report += "✅ user-бот: пользователь доступен\n"
        except Exception as e:
            report += f"❌ user-бот: {str(e)[:100]}\n"

        await message.answer(report, parse_mode="Markdown")

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("debug_state"))
async def debug_state(message: Message, state: FSMContext):
    """Отладка текущего состояния FSM"""
    if message.from_user.id != ADMIN_ID:
        return

    current_state = await state.get_state()
    state_data = await state.get_data()

    await message.answer(
        f"🔍 *Текущее состояние:*\n"
        f"State: {current_state}\n"
        f"Data: {state_data}",
        parse_mode="Markdown"
    )


@router.message(Command("check_state"))
async def check_state(message: Message, state: FSMContext):
    """Проверка текущего состояния FSM"""
    if message.from_user.id != ADMIN_ID:
        return

    current_state = await state.get_state()
    state_data = await state.get_data()

    await message.answer(
        f"🔍 *Текущее состояние:*\n"
        f"State: {current_state}\n"
        f"Data: {state_data}",
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "add_new_link")
async def add_new_link_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки добавления новой ссылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await callback.message.edit_text(
        "📝 Отправьте новую ссылку (должна начинаться с tg://)"
    )
    await state.set_state(AddLinkState.waiting_for_url)
    await callback.answer()

@router.message(Command("debug_links"))
async def debug_links(message: Message):
    """Диагностика ссылок в БД"""
    if message.from_user.id != ADMIN_ID:
        return

    from database.db import get_connection

    with get_connection() as conn:
        cursor = conn.cursor()

        # Все ссылки
        cursor.execute(
            "SELECT id, url, active, created_at, expires_at, complaints_count, deactivated_by_admin FROM links")
        all_links = cursor.fetchall()

        report = "🔍 *Диагностика ссылок:*\n\n"
        report += f"Всего ссылок в БД: {len(all_links)}\n\n"

        for link in all_links:
            report += f"ID: {link['id']}\n"
            report += f"URL: {link['url'][:50]}...\n"
            report += f"Active: {link['active']}\n"
            report += f"Deactivated by admin: {link['deactivated_by_admin']}\n"
            report += f"Created: {link['created_at']}\n"
            report += f"Expires: {link['expires_at']}\n"
            report += f"Complaints: {link['complaints_count']}\n"
            report += "---\n"

        await message.answer(report[:4000], parse_mode="Markdown")

# хэндлер для отладки
@router.message()
async def fallback_handler(message: Message, state: FSMContext):
    """Запасной хэндлер для отладки"""
    if message.from_user.id != ADMIN_ID:
        return

    current_state = await state.get_state()
    logger.info(f"🔍 Fallback got message: '{message.text}', state: {current_state}")

    # Если состояние waiting_for_url, но основной хэндлер не сработал
    if current_state == "AddLinkAfterDeactivation:waiting_for_url":
        logger.warning(f"⚠️ Fallback handler activated for: {message.text}")

        # Проверяем, начинается ли с tg://
        if message.text and message.text.strip().startswith("tg://"):
            # Вызываем основной хэндлер вручную
            await process_new_link_after_deactivation(message, state)
