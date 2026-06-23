from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

router = Router()


async def open_webapp(message: Message):
    """Открывает мини-приложение"""
    # ВАЖНО: замените URL на ваш реальный адрес, где будет hosted index.html
    # Например: https://ваш-сайт.com/app
    # Или для локального теста можно использовать ngrok
    APP_URL = "https://example.com"  # Заглушка

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть приложение",
            web_app=WebAppInfo(url=APP_URL)
        )]
    ])

    await message.answer(
        "📱 <b>Наше приложение</b>\n\n"
        "Нажмите на кнопку, чтобы открыть мини-приложение.\n"
        "В нём вы можете управлять своим профилем, искать вакансии и многое другое!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(Command("app"))
async def app_command(message: Message):
    await open_webapp(message)