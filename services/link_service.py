# services/link_service.py
from database.db import get_connection
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def add_link(url: str) -> Optional[int]:
    """Добавляет новую ссылку и АКТИВИРУЕТ её"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Сначала деактивируем все старые активные ссылки
            cursor.execute("UPDATE links SET active = 0 WHERE active = 1")

            # Добавляем новую ссылку как активную (active=1)
            cursor.execute("""
                INSERT INTO links (url, active, complaints_count, deactivated_by_admin) 
                VALUES (?, 1, 0, 0)
            """, (url,))
            conn.commit()
            link_id = cursor.lastrowid
            logger.info(f"Link added and ACTIVATED: {url} (ID: {link_id}), expires in 30 days")
            return link_id
    except Exception as e:
        logger.error(f"Error adding link: {e}")
        return None


def activate_link(link_id: int) -> bool:
    """Активирует указанную ссылку и деактивирует все остальные"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Деактивируем все активные ссылки
            cursor.execute("UPDATE links SET active = 0 WHERE active = 1")
            # Активируем новую
            cursor.execute("UPDATE links SET active = 1, deactivated_by_admin = 0 WHERE id = ?", (link_id,))
            conn.commit()
            logger.info(f"Link {link_id} activated")
            return True
    except Exception as e:
        logger.error(f"Error activating link {link_id}: {e}")
        return False

def get_current_active_link():
    """Возвращает текущую активную ссылку"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, created_at, expires_at, complaints_count 
                FROM links 
                WHERE active = 1 
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"Error getting active link: {e}")
        return None

def get_all_active_links():
    """Возвращает все активные ссылки"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, created_at, expires_at, complaints_count, deactivated_by_admin
                FROM links 
                WHERE active = 1
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting all active links: {e}")
        return []

def get_expiring_links(days_before: int = 1):
    """Возвращает ссылки, которые истекают через days_before дней"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, created_at, expires_at, complaints_count
                FROM links 
                WHERE active = 1 
                AND deactivated_by_admin = 0
                AND date(expires_at) = date('now', '+? days')
            """, (days_before,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting expiring links: {e}")
        return []

def increment_complaints(link_id: int) -> int:
    """Увеличивает счетчик жалоб для ссылки"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE links 
                SET complaints_count = complaints_count + 1 
                WHERE id = ?
                RETURNING complaints_count
            """, (link_id,))
            result = cursor.fetchone()
            conn.commit()
            new_count = result['complaints_count'] if result else 0
            logger.info(f"Link {link_id} complaints count increased to {new_count}")
            return new_count
    except Exception as e:
        logger.error(f"Error incrementing complaints for link {link_id}: {e}")
        return 0

def deactivate_link(link_id: int, by_admin: bool = True) -> bool:
    """Деактивирует ссылку"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            deactivated_flag = 1 if by_admin else 0
            cursor.execute("""
                UPDATE links 
                SET active = 0, deactivated_by_admin = ? 
                WHERE id = ?
            """, (deactivated_flag, link_id))
            conn.commit()
            logger.info(f"Link {link_id} deactivated (by_admin: {by_admin})")
            return True
    except Exception as e:
        logger.error(f"Error deactivating link: {e}")
        return False

def has_active_link() -> bool:
    """Проверяет, есть ли активная ссылка"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM links WHERE active = 1 AND deactivated_by_admin = 0")
            result = cursor.fetchone()
            return result['cnt'] > 0
    except Exception as e:
        logger.error(f"Error checking active link: {e}")
        return False

def get_link_by_id(link_id: int):
    """Возвращает ссылку по ID"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url, created_at, expires_at, complaints_count 
                FROM links 
                WHERE id = ?
            """, (link_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"Error getting link by ID {link_id}: {e}")
        return None