# user_bot/handlers/payments.py (без изменений)
from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, ContentType
from services.payment_service import create_invoice, handle_successful_payment
from services.link_service import get_current_active_link
from user_bot.keyboards.inline import link_keyboard

router = Router()

@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery):
    await create_invoice(callback.bot, callback.from_user.id)

@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    handle_successful_payment(user_id, username)

    link = get_current_active_link()
    if link:
        await message.answer(
            f"✅ Оплата прошла успешно!\n\nВаша ссылка:\n{link['url']}",
            reply_markup=link_keyboard()
        )
    else:
        await message.answer(
            "✅ Оплата прошла успешно, но пока нет активных ссылок.",
            reply_markup=link_keyboard()
        )