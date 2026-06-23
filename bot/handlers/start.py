from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from database.crud import get_user_by_telegram_id

router = Router()


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👷 Я ищу работу"), KeyboardButton(text="🏢 Я работодатель")]
        ],
        resize_keyboard=True
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)

    if user and user.is_registered:
        if user.role == "worker":
            from bot.handlers.worker_menu import worker_menu
            await worker_menu(message, user)
        else:
            from bot.handlers.employer_menu import employer_menu
            await employer_menu(message, user)
        return

    await message.answer(
        "🤖 <b>Добро пожаловать в JobBot!</b>\n\n"
        "Платформа для поиска работы и сотрудников.\n"
        "👇 <b>Выберите вашу роль:</b>",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("menu"))
async def force_menu(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if user and user.is_registered:
        if user.role == "worker":
            from bot.handlers.worker_menu import worker_menu
            await worker_menu(message, user)
        else:
            from bot.handlers.employer_menu import employer_menu
            await employer_menu(message, user)