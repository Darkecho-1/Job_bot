from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(role: str):
    if role == "worker":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔍 Найти вакансии")],
                [KeyboardButton(text="📋 Мои отклики")],
                [KeyboardButton(text="💎 Подписка")],
                [KeyboardButton(text="ℹ️ О боте")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Создать вакансию")],
                [KeyboardButton(text="📊 Мои вакансии")],
                [KeyboardButton(text="ℹ️ О боте")]
            ],
            resize_keyboard=True
        )