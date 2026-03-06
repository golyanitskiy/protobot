# services/access_service.py
from database.db import get_connection
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def is_access_active(user_id: int) -> bool:
    """Проверяет, активен ли доступ пользователя"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT access_until 
                FROM users 
                WHERE user_id=? AND access_until > datetime('now')
            """, (user_id,))
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking access for user {user_id}: {e}")
        return False


def update_payment(user_id: int, username: str = ""):
    """Обновление доступа после оплаты (30 дней)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            access_until = (datetime.now() + timedelta(days=30)).isoformat()

            cursor.execute("""
                INSERT INTO users (user_id, username, access_until) 
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET 
                    username=excluded.username,
                    access_until=excluded.access_until
            """, (user_id, username, access_until))

            conn.commit()
            logger.info(f"Payment updated for user {user_id}")
            return True

    except Exception as e:
        logger.error(f"Error updating payment for user {user_id}: {e}")
        return False


def get_active_users():
    """Возвращает список пользователей с активным доступом"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, access_until
                FROM users 
                WHERE access_until > datetime('now')
            """)
            rows = cursor.fetchall()

            # Преобразуем Row объекты в словари
            users = []
            for row in rows:
                # Проверяем тип row и создаем словарь
                if hasattr(row, 'keys'):
                    # Это Row объект
                    users.append({
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'access_until': row['access_until']
                    })
                else:
                    # Это кортеж
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'access_until': row[2]
                    })

            logger.info(f"Found {len(users)} active users: {[u['user_id'] for u in users]}")
            return users

    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        return []


def grant_test_access(user_id: int, username: str = ""):
    """Предоставляет тестовый доступ на 30 дней"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, access_until) 
                VALUES (?, ?, datetime('now', '+30 days'))
                ON CONFLICT(user_id) DO UPDATE SET 
                    username = excluded.username,
                    access_until = datetime('now', '+30 days')
            """, (user_id, username))
            conn.commit()
            logger.info(f"Test access granted for user {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error granting test access for user {user_id}: {e}")
        return False


def deactivate_user_access(user_id: int) -> bool:
    """Деактивирует доступ пользователя (например, если он заблокировал бота)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET access_until = NULL 
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            logger.info(f"User {user_id} access deactivated")
            return True
    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        return False