# user_bot/userbot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from config import USER_BOT_TOKEN
from database.db import init_db
from user_bot.handlers.start import router as start_router
from user_bot.handlers.payments import router as payments_router
from user_bot.handlers.links import router as links_router
from services.notification_service import close_notification_bot
from user_bot.handlers.contact import router as contact_router

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция для запуска пользовательского бота"""
    bot = None
    try:
        # Инициализируем БД
        init_db()

        # Создаем бота с правильными параметрами для aiogram 3.x
        bot = Bot(
            token=USER_BOT_TOKEN,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML
            )
        )

        # Создаем диспетчер
        dp = Dispatcher(storage=MemoryStorage())

        # Подключаем роутеры
        dp.include_router(start_router)
        dp.include_router(payments_router)
        dp.include_router(links_router)
        dp.include_router(contact_router)

        # Устанавливаем команды бота
        await bot.set_my_commands([
            BotCommand(command="start", description="Запустить бота, получить ссылку"),
            BotCommand(command="test_access", description="Тестовый доступ (для разработки)"),
        ])

        logger.info("🤖 User Bot started!")
        print("User Bot запущен!")

        # Запускаем polling
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("User bot stopping...")
    except Exception as e:
        logger.error(f"Error in user bot: {e}")
    finally:
        # Корректно закрываем все соединения
        if bot:
            await bot.session.close()
        await close_notification_bot()  # это правильно
        logger.info("User bot finished")


if __name__ == "__main__":
    asyncio.run(main())