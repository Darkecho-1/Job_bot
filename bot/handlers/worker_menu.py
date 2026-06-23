import os
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.crud import get_user_by_telegram_id, update_user
from database.engine import async_session_maker
from database.models import Application, Vacancy, Tariff, Subscription
from sqlalchemy import select, update, delete
from datetime import datetime, timedelta
from bot.handlers.vacancy_matching import find_vacancies
from services.geolocation import get_city_from_coords

router = Router()


# ============ ГЛАВНОЕ МЕНЮ СОИСКАТЕЛЯ ============
async def worker_menu(message: Message, user):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Найти вакансии")],
            [KeyboardButton(text="📋 Мои отклики")],
            [KeyboardButton(text="💎 Подписка")],
            [KeyboardButton(text="📍 Изменить город"), KeyboardButton(text="🔄 Тип работы")],
            [KeyboardButton(text="🗑 Удалить профиль"), KeyboardButton(text="📱 Приложение"),
             KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"👋 <b>Здравствуйте, {user.first_name or user.username}!</b>\n\n"
        f"Вы зарегистрированы как <b>соискатель</b>.\n"
        f"Ваш город: {user.city or 'не указан'}\n"
        f"Тип работы: {user.preferred_work_type}\n\n"
        f"Используйте кнопки для поиска работы.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============ НАЙТИ ВАКАНСИИ ============
@router.message(F.text == "🔍 Найти вакансии")
async def find_vacancies_handler(message: Message):
    await find_vacancies(message)


# ============ МОИ ОТКЛИКИ ============
@router.message(F.text == "📋 Мои отклики")
async def my_applications(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    async with async_session_maker() as session:
        result = await session.execute(
            select(Application).where(Application.worker_id == user.id).order_by(Application.created_at.desc())
        )
        apps = result.scalars().all()

    if not apps:
        await message.answer("📭 У вас пока нет откликов.\n\nИспользуйте «🔍 Найти вакансии» для поиска работы.")
        return

    text = "📋 <b>Ваши отклики:</b>\n\n"
    for app in apps:
        async with async_session_maker() as session:
            vac_result = await session.execute(select(Vacancy).where(Vacancy.id == app.vacancy_id))
            vacancy = vac_result.scalar_one_or_none()

        status_ru = {
            "pending": "⏳ Ожидает ответа",
            "accepted": "✅ Принят 🎉",
            "rejected": "❌ Отклонен"
        }.get(app.status, app.status)

        text += f"• {vacancy.title if vacancy else 'Вакансия удалена'} — {status_ru}\n"
        text += f"  ID вакансии: {app.vacancy_id}\n\n"

    await message.answer(text, parse_mode="HTML")


# ============ ПОДПИСКА ============
@router.message(F.text == "💎 Подписка")
async def subscription_menu(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != "worker":
        await message.answer("❌ Подписка доступна только для соискателей")
        return

    async with async_session_maker() as session:
        tariffs = await session.execute(select(Tariff).where(Tariff.is_active == True))
        tariffs = tariffs.scalars().all()

    if not tariffs:
        await message.answer("📭 Тарифы временно недоступны")
        return

    text = "💎 <b>Доступные тарифы подписки</b>\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for tariff in tariffs:
        text += f"• <b>{tariff.name}</b>: {tariff.price} руб. — {tariff.days} дней\n"
        text += f"  {tariff.description or ''}\n\n"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"Оформить {tariff.name}", callback_data=f"subscribe_{tariff.id}")
        ])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("subscribe_"))
async def process_subscription(callback: CallbackQuery):
    tariff_id = int(callback.data.split("_")[1])
    user = await get_user_by_telegram_id(callback.from_user.id)

    async with async_session_maker() as session:
        tariff = await session.execute(select(Tariff).where(Tariff.id == tariff_id))
        tariff = tariff.scalar_one_or_none()

        if not tariff:
            await callback.answer("❌ Тариф не найден", show_alert=True)
            return

    # Проверяем, есть ли активная подписка
    async with async_session_maker() as session:
        existing_sub = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
                Subscription.expires_at > datetime.now()
            )
        )
        if existing_sub.scalar_one_or_none():
            await callback.answer("❌ У вас уже есть активная подписка", show_alert=True)
            return

    # Создаем новую подписку
    async with async_session_maker() as session:
        new_sub = Subscription(
            user_id=user.id,
            tariff_id=tariff.id,
            started_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=tariff.days),
            is_active=True
        )
        session.add(new_sub)
        await session.commit()

        await callback.message.answer(
            f"✅ <b>Подписка «{tariff.name}» оформлена!</b>\n\n"
            f"💰 Стоимость: {tariff.price} руб.\n"
            f"⏰ Действует до: {new_sub.expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Теперь вам доступны <b>закрытые вакансии</b>!",
            parse_mode="HTML"
        )
        await callback.answer()


# ============ ИЗМЕНИТЬ ГОРОД ============
class ChangeCityState(StatesGroup):
    waiting_location = State()


@router.message(F.text == "📍 Изменить город")
async def change_city_start(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить местоположение", request_location=True)]],
        resize_keyboard=True
    )
    await state.set_state(ChangeCityState.waiting_location)
    await message.answer(
        "📍 <b>Изменение города</b>\n\n"
        "Нажмите на кнопку ниже и отправьте ваше текущее местоположение.\n"
        "Город определится автоматически.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(ChangeCityState.waiting_location, F.location)
async def change_city_save(message: Message, state: FSMContext):
    city_info = await get_city_from_coords(message.location.latitude, message.location.longitude)
    city = city_info.get("city", "Не определен")
    district = city_info.get("district", "")

    await update_user(
        message.from_user.id,
        latitude=message.location.latitude,
        longitude=message.location.longitude,
        city=city,
        district=district
    )

    await state.clear()
    await message.answer(
        f"✅ Город обновлён: <b>{city}</b>\n"
        f"Район: {district if district else 'не определен'}\n\n"
        f"Теперь вам будут показываться вакансии с учётом нового города.",
        parse_mode="HTML"
    )

    user = await get_user_by_telegram_id(message.from_user.id)
    await worker_menu(message, user)


# ============ ТИП РАБОТЫ ============
@router.message(F.text == "🔄 Тип работы")
async def change_work_type_menu(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != "worker":
        await message.answer("❌ Только для соискателей")
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🖥 Онлайн работа")],
            [KeyboardButton(text="🏢 Физическая работа")],
            [KeyboardButton(text="🔀 Оба варианта")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

    current_type = {
        "online": "🖥 Онлайн",
        "physical": "🏢 Физическая",
        "both": "🔀 Оба варианта"
    }.get(user.preferred_work_type, "не указан")

    await message.answer(
        f"🔄 <b>Выберите тип работы:</b>\n\n"
        f"Текущий тип: {current_type}\n\n"
        f"🖥 Онлайн — удалённая работа\n"
        f"🏢 Физическая — работа в офисе/на месте\n"
        f"🔀 Оба варианта — и то, и другое",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(F.text.in_(["🖥 Онлайн работа", "🏢 Физическая работа", "🔀 Оба варианта"]))
async def save_work_type(message: Message):
    type_map = {
        "🖥 Онлайн работа": "online",
        "🏢 Физическая работа": "physical",
        "🔀 Оба варианта": "both"
    }
    new_type = type_map.get(message.text)

    if new_type:
        await update_user(message.from_user.id, preferred_work_type=new_type)
        await message.answer(
            f"✅ Тип работы изменён на: <b>{message.text}</b>\n\n"
            f"🔍 Теперь вам будут показываться только подходящие вакансии.",
            parse_mode="HTML"
        )

    user = await get_user_by_telegram_id(message.from_user.id)
    await worker_menu(message, user)


@router.message(F.text == "🔙 Назад")
async def back_to_worker_menu(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    await worker_menu(message, user)


# ============ УДАЛЕНИЕ ПРОФИЛЯ ============
@router.message(F.text == "🗑 Удалить профиль")
async def delete_profile_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚠️ ДА, УДАЛИТЬ", callback_data="confirm_delete_worker_profile"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_profile")
        ]
    ])

    await message.answer(
        "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        "Вы собираетесь удалить свой профиль.\n\n"
        "❌ Все ваши отклики будут удалены\n"
        "❌ Вы потеряете доступ к истории\n\n"
        "<i>После удаления вы сможете зарегистрироваться заново.</i>\n\n"
        "Вы уверены?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_delete_worker_profile")
async def confirm_delete_worker_profile(callback: CallbackQuery):
    from database.models import User, Application
    from sqlalchemy import delete

    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Профиль не найден")
        await callback.answer()
        return

    async with async_session_maker() as session:
        await session.execute(delete(Application).where(Application.worker_id == user.id))
        await session.execute(delete(User).where(User.telegram_id == callback.from_user.id))
        await session.commit()

    await callback.message.edit_text(
        "✅ <b>Ваш профиль удалён!</b>\n\n"
        "Отправьте /start, чтобы зарегистрироваться заново.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_delete_profile")
async def cancel_delete_profile(callback: CallbackQuery):
    await callback.message.edit_text("✅ Удаление профиля отменено")
    await callback.answer()


# ============ ПРИЛОЖЕНИЕ ============
@router.message(F.text == "📱 Приложение")
async def open_app(message: Message):
    from bot.handlers.webapp import open_webapp
    await open_webapp(message)


# ============ О БОТЕ ============
@router.message(F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    await message.answer(
        "🤖 <b>JobBot v2.0</b>\n\n"
        "Платформа для поиска работы и сотрудников.\n"
        "Работодатели размещают вакансии.\n"
        "Соискатели находят работу.\n\n"
        "📞 По вопросам: @ваш_чат_поддержки",
        parse_mode="HTML"
    )