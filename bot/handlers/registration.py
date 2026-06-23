from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import datetime

from database.crud import create_user, update_user, get_user_by_telegram_id
from services.geolocation import get_city_from_coords
from utils.validators import sanitize_text

router = Router()

contact_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]],
    resize_keyboard=True
)

location_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📍 Отправить местоположение", request_location=True)]],
    resize_keyboard=True
)


class WorkerRegistration(StatesGroup):
    waiting_contact = State()
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_patronymic = State()
    waiting_birth_date = State()
    waiting_location = State()
    waiting_work_type = State()


class EmployerRegistration(StatesGroup):
    waiting_contact = State()
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_patronymic = State()
    waiting_birth_date = State()


@router.message(F.text.in_(["👷 Я ищу работу", "🏢 Я работодатель"]))
async def role_selected(message: Message, state: FSMContext):
    role = "worker" if "работу" in message.text else "employer"
    await state.update_data(role=role)

    existing = await get_user_by_telegram_id(message.from_user.id)
    if not existing:
        await create_user(message.from_user.id, role, message.from_user.first_name, message.from_user.username)

    if role == "worker":
        await state.set_state(WorkerRegistration.waiting_contact)
        await message.answer("📞 Подтвердите номер телефона:", reply_markup=contact_keyboard)
    else:
        await state.set_state(EmployerRegistration.waiting_contact)
        await message.answer("📞 Подтвердите номер телефона (работодатель):", reply_markup=contact_keyboard)


@router.message(WorkerRegistration.waiting_contact, F.contact)
async def worker_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(WorkerRegistration.waiting_first_name)
    await message.answer("Введите ваше ИМЯ:", reply_markup=ReplyKeyboardRemove())


@router.message(WorkerRegistration.waiting_first_name)
async def worker_first_name(message: Message, state: FSMContext):
    name = sanitize_text(message.text, 50)
    if len(name) < 2:
        await message.answer("Слишком коротко. Введите снова:")
        return
    await state.update_data(first_name=name)
    await state.set_state(WorkerRegistration.waiting_last_name)
    await message.answer("Введите ФАМИЛИЮ:")


@router.message(WorkerRegistration.waiting_last_name)
async def worker_last_name(message: Message, state: FSMContext):
    name = sanitize_text(message.text, 50)
    await state.update_data(last_name=name)
    await state.set_state(WorkerRegistration.waiting_patronymic)
    await message.answer("Введите ОТЧЕСТВО (или '-'):")


@router.message(WorkerRegistration.waiting_patronymic)
async def worker_patronymic(message: Message, state: FSMContext):
    val = sanitize_text(message.text, 50)
    if val == "-":
        val = ""
    await state.update_data(patronymic=val)
    await state.set_state(WorkerRegistration.waiting_birth_date)
    await message.answer("Дата рождения ДД.ММ.ГГГГ:")


@router.message(WorkerRegistration.waiting_birth_date)
async def worker_birth_date(message: Message, state: FSMContext):
    date_text = message.text.strip().replace('.', '/')
    # Поддерживаем форматы: 02.08.2006, 2.8.2006, 02/08/2006, 2/8/2006
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d/%m/%y"):
        try:
            bd = datetime.datetime.strptime(date_text, fmt)
            break
        except ValueError:
            continue
    else:
        await message.answer("❌ Неверный формат. Используйте ДД.ММ.ГГГГ (например: 02.08.2006 или 2.8.2006)")
        return

    age = (datetime.datetime.now() - bd).days // 365
    if age < 14 or age > 100:
        await message.answer("❌ Возраст должен быть от 14 до 100 лет")
        return

    await state.update_data(birth_date=bd)
    await state.set_state(WorkerRegistration.waiting_location)
    await message.answer("📍 Отправьте геолокацию:", reply_markup=location_keyboard)


@router.message(WorkerRegistration.waiting_location, F.location)
async def worker_location(message: Message, state: FSMContext):
    city_info = await get_city_from_coords(message.location.latitude, message.location.longitude)
    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude,
        city=city_info.get("city", "Не определен"),
        district=city_info.get("district", "")
    )

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🖥 Онлайн")],
            [KeyboardButton(text="🏢 Физическая")],
            [KeyboardButton(text="🔀 Оба варианта")]
        ],
        resize_keyboard=True
    )
    await state.set_state(WorkerRegistration.waiting_work_type)
    await message.answer(f"Ваш город: {city_info.get('city', 'не определен')}\n\nТип работы:", reply_markup=kb)


@router.message(WorkerRegistration.waiting_work_type)
async def worker_work_type(message: Message, state: FSMContext):
    mapping = {"🖥 Онлайн": "online", "🏢 Физическая": "physical", "🔀 Оба варианта": "both"}
    work_type = mapping.get(message.text, "both")
    await state.update_data(preferred_work_type=work_type, is_registered=True)

    data = await state.get_data()
    await update_user(message.from_user.id, **data)
    await state.clear()

    user = await get_user_by_telegram_id(message.from_user.id)
    from bot.handlers.worker_menu import worker_menu
    await worker_menu(message, user)


@router.message(EmployerRegistration.waiting_contact, F.contact)
async def employer_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(EmployerRegistration.waiting_first_name)
    await message.answer("Введите ваше ИМЯ:", reply_markup=ReplyKeyboardRemove())


@router.message(EmployerRegistration.waiting_first_name)
async def employer_first_name(message: Message, state: FSMContext):
    name = sanitize_text(message.text, 50)
    await state.update_data(first_name=name)
    await state.set_state(EmployerRegistration.waiting_last_name)
    await message.answer("Введите ФАМИЛИЮ:")


@router.message(EmployerRegistration.waiting_last_name)
async def employer_last_name(message: Message, state: FSMContext):
    name = sanitize_text(message.text, 50)
    await state.update_data(last_name=name)
    await state.set_state(EmployerRegistration.waiting_patronymic)
    await message.answer("Введите ОТЧЕСТВО (или '-'):")


@router.message(EmployerRegistration.waiting_patronymic)
async def employer_patronymic(message: Message, state: FSMContext):
    val = sanitize_text(message.text, 50)
    if val == "-":
        val = ""
    await state.update_data(patronymic=val)
    await state.set_state(EmployerRegistration.waiting_birth_date)
    await message.answer("Дата рождения ДД.ММ.ГГГГ:")


@router.message(EmployerRegistration.waiting_birth_date)
async def employer_birth_date(message: Message, state: FSMContext):
    date_text = message.text.strip().replace('.', '/')
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%d/%m/%y"):
        try:
            bd = datetime.datetime.strptime(date_text, fmt)
            break
        except ValueError:
            continue
    else:
        await message.answer("❌ Неверный формат. Используйте ДД.ММ.ГГГГ (например: 02.08.2006 или 2.8.2006)")
        return

    await state.update_data(birth_date=bd, is_registered=True)
    data = await state.get_data()
    await update_user(message.from_user.id, **data)
    await state.clear()

    user = await get_user_by_telegram_id(message.from_user.id)
    from bot.handlers.employer_menu import employer_menu
    await employer_menu(message, user)