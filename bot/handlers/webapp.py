from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

router = Router()

# Ссылка на мини-приложение (замените на свою)
APP_URL = "https://Darkecho-1.github.io/Job_bot/webapp/index.html"

@router.message(Command("app"))
async def open_webapp(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть приложение",
            web_app=WebAppInfo(url=APP_URL)
        )]
    ])
    await message.answer(
        "📱 <b>Мини-приложение JobBot</b>\n\n"
        "Нажмите на кнопку, чтобы открыть.\n"
        "Здесь вы можете управлять профилем, искать вакансии и общаться.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def open_webapp_from_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть приложение",
            web_app=WebAppInfo(url=APP_URL)
        )]
    ])
    await message.answer(
        "📱 <b>Мини-приложение</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )