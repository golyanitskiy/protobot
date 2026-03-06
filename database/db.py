# database/db.py
import logging
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "protobot.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

logger = logging.getLogger(__name__)


def get_connection():
    """Возвращает соединение с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация структуры БД"""
    conn = get_connection()
    c = conn.cursor()

    # Таблица пользователей
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        access_until TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # Таблица ссылок - создаем с нуля правильную структуру
    c.execute("""
    CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        expires_at TEXT DEFAULT (datetime('now', '+30 days')),
        active INTEGER DEFAULT 0,
        complaints_count INTEGER DEFAULT 0,
        deactivated_by_admin INTEGER DEFAULT 0
    )
    """)

    # Проверяем и добавляем отсутствующие колонки (на случай, если таблица уже существовала)
    try:
        c.execute("SELECT expires_at FROM links LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE links ADD COLUMN expires_at TEXT DEFAULT (datetime('now', '+30 days'))")
        logger.info("Added expires_at column")

    try:
        c.execute("SELECT deactivated_by_admin FROM links LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE links ADD COLUMN deactivated_by_admin INTEGER DEFAULT 0")
        logger.info("Added deactivated_by_admin column")

    # Индексы для производительности
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_access ON users(access_until)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_links_active ON links(active)")

    # Создаем индекс только если колонка существует
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_links_expires ON links(expires_at)")
        logger.info("Created expires_at index")
    except sqlite3.OperationalError as e:
        logger.warning(f"Could not create expires_at index: {e}")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")