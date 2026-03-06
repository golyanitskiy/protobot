from aiogram import Router
from aiogram.types import Message
from services.link_service import add_link
from services.access_service import get_active_users

router = Router()

# Настроим так: если сообщение — ссылка, добавляем и рассылаем
@router.message()
async def new_link_handler(message: Message):
    url = message.text.strip()
    if not url.startswith("tg://"):
        await message.reply("❌ Ссылка должна начинаться с tg://")
        return

    # Добавляем ссылку в БД
    add_link(url)

    # Получаем всех пользователей с активным доступом
    users = get_active_users()

    for user_id in users:
        try:
            await message.bot.send_message(user_id, f"📢 Новая ссылка:\n{url}")
        except Exception as e:
            print(f"Не удалось отправить пользователю {user_id}: {e}")

    await message.reply(f"✅ Ссылка добавлена и разослана {len(users)} пользователям.")