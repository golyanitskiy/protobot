# main_multiprocess.py
import multiprocessing
import logging
import sys
import signal
from database.db import init_db
from pathlib import Path

# Добавляем корневую директорию проекта в PATH
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_user_bot_process():
    """Запуск пользовательского бота в отдельном процессе"""
    import sys
    import asyncio
    from pathlib import Path

    # Добавляем путь в дочернем процессе
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    try:
        from user_bot.userbot import main as user_main
        asyncio.run(user_main())
    except KeyboardInterrupt:
        logger.info("User bot process stopped by user")
    except Exception as outer_e:
        logger.error(f"Error in user bot process: {outer_e}")
    finally:
        # Закрываем все соединения
        try:
            from services.notification_service import close_notification_bot
            asyncio.run(close_notification_bot())
        except Exception as inner_e:
            logger.error(f"Error closing notification bot: {inner_e}")
        logger.info("User bot process finished")


def run_admin_bot_process():
    """Запуск админ-бота в отдельном процессе"""
    import sys
    import asyncio
    from pathlib import Path

    # Добавляем путь в дочернем процессе
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    try:
        from admin_bot.adminbot import main as admin_main
        asyncio.run(admin_main())
    except KeyboardInterrupt:
        logger.info("Admin bot process stopped by user")
    except Exception as outer_e:
        logger.error(f"Error in admin bot process: {outer_e}")
    finally:
        logger.info("Admin bot process finished")


if __name__ == "__main__":
    # Для macOS важно установить метод запуска
    if sys.platform == "darwin":  # macOS
        multiprocessing.set_start_method('spawn', force=True)

    # Инициализируем БД в основном процессе
    init_db()
    logger.info("Database initialized")

    # Создаем процессы для ботов
    user_process = multiprocessing.Process(
        target=run_user_bot_process,
        name="UserBot"
    )

    admin_process = multiprocessing.Process(
        target=run_admin_bot_process,
        name="AdminBot"
    )


    def signal_handler(signum, _):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"Received signal {signum}, stopping bots...")
        user_process.terminate()
        admin_process.terminate()

        # Даем время на завершение
        user_process.join(timeout=5)
        admin_process.join(timeout=5)

        # Если процессы не завершились, убиваем принудительно
        if user_process.is_alive():
            user_process.kill()
        if admin_process.is_alive():
            admin_process.kill()

        logger.info("All bots stopped")
        sys.exit(0)


    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Запускаем процессы
        user_process.start()
        admin_process.start()

        logger.info("✅ Both bots started successfully!")

        # Ждем завершения процессов
        user_process.join()
        admin_process.join()

    except KeyboardInterrupt:
        logger.info("🛑 Stopping bots...")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Error: {e}")
        user_process.terminate()
        admin_process.terminate()
        user_process.join(timeout=5)
        admin_process.join(timeout=5)