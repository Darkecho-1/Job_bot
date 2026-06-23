from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os

from database.crud import get_user_by_telegram_id, create_vacancy
from database.crud import activate_vacancy
from services.payment_processor import create_payment_link

router = Router()


class CreateVacancy(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_work_type = State()
    waiting_location_city = State()
    waiting_location_address = State()
    waiting_salary_min = State()
    waiting_salary_max = State()
    waiting_requirements = State()
    waiting_responsibilities = State()


@router.message(F.text == "➕ Создать вакансию")
async def start_create(message: Message, state: FSMContext):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != "employer":
        await message.answer("❌ Только работодатели могут создавать вакансии")
        return
    await state.set_state(CreateVacancy.waiting_title)
    await message.answer("📝 Введите НАЗВАНИЕ вакансии:")


@router.message(CreateVacancy.waiting_title)
async def title_handler(message: Message, state: FSMContext):
    if len(message.text) < 5:
        await message.answer("Минимум 5 символов")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateVacancy.waiting_description)
    await message.answer("📄 Введите ОПИСАНИЕ вакансии:")


@router.message(CreateVacancy.waiting_description)
async def desc_handler(message: Message, state: FSMContext):
    if len(message.text) < 20:
        await message.answer("Минимум 20 символов")
        return
    await state.update_data(description=message.text.strip())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖥 Онлайн", callback_data="wt_online")],
        [InlineKeyboardButton(text="🏢 Физическая", callback_data="wt_physical")],
        [InlineKeyboardButton(text="🔀 Оба", callback_data="wt_both")]
    ])
    await state.set_state(CreateVacancy.waiting_work_type)
    await message.answer("🏷 Выберите тип работы:", reply_markup=kb)


@router.callback_query(CreateVacancy.waiting_work_type, F.data.startswith("wt_"))
async def work_type_handler(callback: CallbackQuery, state: FSMContext):
    mapping = {"wt_online": "online", "wt_physical": "physical", "wt_both": "both"}
    work_type = mapping[callback.data]
    await state.update_data(work_type=work_type)
    if work_type == "physical":
        await state.set_state(CreateVacancy.waiting_location_city)
        await callback.message.answer("🏙 Введите ГОРОД:")
    else:
        await state.update_data(location_city="", location_address="")
        await state.set_state(CreateVacancy.waiting_salary_min)
        await callback.message.answer("💰 МИНИМАЛЬНАЯ зарплата (руб):")
    await callback.answer()


@router.message(CreateVacancy.waiting_location_city)
async def city_handler(message: Message, state: FSMContext):
    await state.update_data(location_city=message.text.strip())
    await state.set_state(CreateVacancy.waiting_location_address)
    await message.answer("📍 АДРЕС или район:")


@router.message(CreateVacancy.waiting_location_address)
async def address_handler(message: Message, state: FSMContext):
    await state.update_data(location_address=message.text.strip())
    await state.set_state(CreateVacancy.waiting_salary_min)
    await message.answer("💰 МИНИМАЛЬНАЯ зарплата (руб):")


@router.message(CreateVacancy.waiting_salary_min)
async def salary_min_handler(message: Message, state: FSMContext):
    try:
        await state.update_data(salary_min=float(message.text.strip()))
        await state.set_state(CreateVacancy.waiting_salary_max)
        await message.answer("💰 МАКСИМАЛЬНАЯ зарплата (руб):")
    except:
        await message.answer("Введите число")


@router.message(CreateVacancy.waiting_salary_max)
async def salary_max_handler(message: Message, state: FSMContext):
    try:
        await state.update_data(salary_max=float(message.text.strip()))
        await state.set_state(CreateVacancy.waiting_requirements)
        await message.answer("📋 ТРЕБОВАНИЯ к кандидату:")
    except:
        await message.answer("Введите число")


@router.message(CreateVacancy.waiting_requirements)
async def requirements_handler(message: Message, state: FSMContext):
    await state.update_data(requirements=message.text.strip())
    await state.set_state(CreateVacancy.waiting_responsibilities)
    await message.answer("📝 ОБЯЗАННОСТИ:")


@router.message(CreateVacancy.waiting_responsibilities)
async def responsibilities_handler(message: Message, state: FSMContext):
    await state.update_data(responsibilities=message.text.strip())
    data = await state.get_data()
    user = await get_user_by_telegram_id(message.from_user.id)

    vacancy = await create_vacancy(
        employer_id=user.id,
        title=data['title'],
        description=data['description'],
        work_type=data['work_type'],
        location_city=data.get('location_city'),
        location_address=data.get('location_address'),
        salary_min=data.get('salary_min'),
        salary_max=data.get('salary_max'),
        salary_text=f"{data.get('salary_min')} - {data.get('salary_max')} руб.",
        requirements=data.get('requirements'),
        responsibilities=data.get('responsibilities')
    )

    await state.clear()

    # В тестовом режиме публикуем сразу
    if os.getenv("TEST_MODE") == "true":
        await activate_vacancy(vacancy.id)
        await message.answer(
            f"✅ <b>Вакансия опубликована (ТЕСТОВЫЙ РЕЖИМ)!</b>\n\n"
            f"📌 {data['title']}\n"
            f"💰 Стоимость: 0 руб. (тест)",
            parse_mode="HTML"
        )
        return

    # Боевой режим — оплата
    price = float(os.getenv("VACANCY_PRICE_NORMAL", 400))
    payment_url, payment_id = await create_payment_link(
        amount=price,
        description=f"Вакансия: {data['title']}",
        user_id=user.id,
        purpose="vacancy_post",
        vacancy_id=vacancy.id
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)]
    ])
    await message.answer(
        f"✅ <b>Вакансия создана!</b>\n\n"
        f"📌 {data['title']}\n"
        f"💰 Для публикации оплатите {price} руб.",
        reply_markup=kb,
        parse_mode="HTML"
    )