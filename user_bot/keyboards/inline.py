# user_bot/keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def buy_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для оплаты Telegram Stars"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Оплатить 100 Stars", callback_data="buy")
    return builder.as_markup()

def link_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой жалобы на ссылку"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ Ссылка не работает", callback_data="report_broken_link")
    builder.button(text="📝 Написать обращение", callback_data="contact_admin")
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены действия"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_contact")
    return builder.as_markup()
