# services/complaint_service.py
from database.db import get_connection
import logging

logger = logging.getLogger(__name__)


def register_complaint(user_id: int, link_id: int) -> dict:
    """
    Регистрирует жалобу, но НЕ деактивирует ссылку.
    Возвращает информацию о жалобе.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Добавляем жалобу
            cursor.execute("""
                INSERT INTO complaints (user_id, link_id, created_at)
                VALUES (?, ?, datetime('now'))
            """, (user_id, link_id))

            # Получаем количество жалоб на эту ссылку
            cursor.execute("SELECT COUNT(*) as cnt FROM complaints WHERE link_id = ?", (link_id,))
            count = cursor.fetchone()['cnt']

            conn.commit()

            return {
                'complaint_id': cursor.lastrowid,
                'total_complaints': count,
                'success': True
            }

    except Exception as e:
        logger.error(f"Error registering complaint: {e}")
        return {'success': False, 'error': str(e)}


def has_active_complaint_flow() -> bool:
    """
    Проверяет, есть ли активный процесс жалобы (нет активной ссылки)
    """
    try:
        from services.link_service import has_active_link
        return not has_active_link()
    except Exception as e:
        logger.error(f"Error checking active complaint flow: {e}")
        return False


def get_complaints(limit: int = 50):
    """Возвращает последние жалобы"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.*, u.username, l.url 
                FROM complaints c
                LEFT JOIN users u ON c.user_id = u.user_id
                LEFT JOIN links l ON c.link_id = l.id
                ORDER BY c.created_at DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting complaints: {e}")
        return []