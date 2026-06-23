from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("check_payment"))
async def check_payment(message: Message):
    await message.answer("ℹ️ Статус платежа можно проверить в админ-панели.")