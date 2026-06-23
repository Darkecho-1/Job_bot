from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.crud import get_user_by_telegram_id, create_application, get_vacancy_by_id
from services.matcher import find_matching_vacancies

router = Router()
user_vacancy_index = {}

async def find_vacancies(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != "worker":
        await message.answer("❌ Только соискатели могут искать вакансии")
        return
    vacancies = await find_matching_vacancies(message.from_user.id)
    if not vacancies:
        await message.answer("😔 Нет подходящих вакансий.")
        return
    user_vacancy_index[message.from_user.id] = {"vacancies": vacancies, "current": 0}
    await show_vacancy(message, message.from_user.id)

async def show_vacancy(message: Message, user_id: int):
    data = user_vacancy_index.get(user_id, {"vacancies": [], "current": 0})
    vacancies = data["vacancies"]
    current = data["current"]
    if current >= len(vacancies):
        await message.answer("🏁 Вы просмотрели все вакансии!")
        return
    vac = vacancies[current]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отказаться", callback_data=f"vac_next_{vac.id}"),
         InlineKeyboardButton(text="✅ Откликнуться", callback_data=f"vac_apply_{vac.id}")]
    ])
    await message.answer(
        f"📌 <b>Вакансия {current+1}/{len(vacancies)}</b>\n\n"
        f"<b>{vac.title}</b>\n\n"
        f"📝 {vac.description}\n\n"
        f"💰 Зарплата: {vac.salary_text or 'не указана'}\n"
        f"📍 Локация: {vac.location_city or 'удаленно'}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("vac_next_"))
async def next_vacancy(callback: CallbackQuery):
    data = user_vacancy_index.get(callback.from_user.id)
    if data:
        data["current"] += 1
        await show_vacancy(callback.message, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data.startswith("vac_apply_"))
async def apply_vacancy(callback: CallbackQuery):
    vacancy_id = int(callback.data.split("_")[2])
    worker = await get_user_by_telegram_id(callback.from_user.id)
    if not worker:
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    await create_application(vacancy_id=vacancy_id, worker_id=worker.id)
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=f"✅ <b>Вы откликнулись на вакансию!</b>",
        parse_mode="HTML"
    )
    await callback.answer("✅ Отклик отправлен!")
    data = user_vacancy_index.get(callback.from_user.id)
    if data:
        data["current"] += 1
        await show_vacancy(callback.message, callback.from_user.id)