from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from database.crud import get_user_by_telegram_id

router = Router()

@router.message(Command("subscribe"))
async def show_tariffs(message: Message):
    await message.answer("💎 Тарифы подписки будут доступны в ближайшее время.")