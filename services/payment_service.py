from aiogram.types import LabeledPrice
from services.access_service import update_payment

async def create_invoice(bot, chat_id):
    prices = [LabeledPrice(label="Доступ 30 дней", amount=100)]
    return bot.send_invoice(
        chat_id=chat_id,
        title="Доступ к ссылкам",
        description="После оплаты получите ссылку",
        payload="access_payment",
        currency="XTR",
        prices=prices
    )

def handle_successful_payment(user_id, username):
    update_payment(user_id, username)