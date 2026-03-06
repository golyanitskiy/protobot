from database.db import get_connection
from datetime import datetime, timedelta

# Проверка, активен ли доступ пользователя (оплата не старше 30 дней)
def is_access_active(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT last_payment_date FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return False
    last_payment = datetime.fromisoformat(row[0])
    return datetime.now() - last_payment <= timedelta(days=30)

# Обновление даты последней оплаты (используется для теста)
def update_payment(user_id: int, username: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, username, last_payment) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(user_id) DO UPDATE SET last_payment=datetime('now'), username=?",
        (user_id, username, username)
    )
    conn.commit()
    conn.close()

# Получение всех пользователей с активным доступом
def get_active_users():
    """Возвращает список пользователей с активным доступом"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Исправляем: проверяем access_until, а не last_payment
            cursor.execute('''
                SELECT id, username, access_until 
                FROM users 
                WHERE access_until > datetime('now')
            ''')
            users = cursor.fetchall()
            return [dict(user) for user in users]  # или return users, если нужны Row объекты
    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        return []