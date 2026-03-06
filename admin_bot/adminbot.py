# admin_bot/adminbot.py
import asyncio
import logging
from admin_bot.handlers import start, links_handler
from admin_bot.handlers.reply import router as reply_router
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from config import ADMIN_BOT_TOKEN
from database.db import init_db
from services.scheduler_service import start_scheduler

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция для запуска админ-бота"""
    bot = None
    try:
        # Инициализируем БД
        init_db()

        bot = Bot(
            token=ADMIN_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        # Запускаем планировщик
        await start_scheduler()

        bot = Bot(
            token=ADMIN_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        dp = Dispatcher(storage=MemoryStorage())

        # Подключаем роутеры
        dp.include_router(start.router)
        dp.include_router(links_handler.router)
        dp.include_router(reply_router)

        await bot.set_my_commands([
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="add_link", description="Добавить новую ссылку"),
            BotCommand(command="links", description="Показать активную ссылку"),
            BotCommand(command="cancel", description="Отменить действие"),
        ])

        logger.info("👮‍♂️ Admin Bot started!")
        print("Admin Bot запущен!")

        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("Admin bot stopping...")
    except Exception as e:
        logger.error(f"Error in admin bot: {e}")
    finally:
        if bot:
            await bot.session.close()
        logger.info("Admin bot finished")


if __name__ == "__main__":
    asyncio.run(main())