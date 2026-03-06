import os
from dotenv import load_dotenv

load_dotenv()

USER_BOT_TOKEN = os.getenv("USER_BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Для продакшна можно добавить:
DATABASE_PATH = 'protobot.db'
LOG_LEVEL = 'ERROR'