import os
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery
from database.crud import get_user_by_telegram_id, get_vacancies_by_employer, get_vacancy_by_id
from database.engine import async_session_maker
from database.models import Vacancy, User, Application, Payment, Subscription
from sqlalchemy import update, delete, select

router = Router()

YOUR_CARD_NUMBER = "1234 5678 9012 3456"


# ============ ГЛАВНОЕ МЕНЮ РАБОТОДАТЕЛЯ ============
async def employer_menu(message: Message, user):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать вакансию")],
            [KeyboardButton(text="💰 Оплатить вакансию"), KeyboardButton(text="❌ Удалить вакансию")],
            [KeyboardButton(text="📊 Мои вакансии"), KeyboardButton(text="📋 Все отклики")],
            [KeyboardButton(text="🗑 Удалить профиль"), KeyboardButton(text="📱 Приложение"),
             KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"🏢 <b>Здравствуйте, {user.first_name or user.username}!</b>\n\n"
        f"Вы зарегистрированы как <b>работодатель</b>.\n"
        f"Стоимость размещения вакансии: {os.getenv('VACANCY_PRICE_NORMAL', 400)} руб.\n\n"
        f"Используйте кнопки для управления вакансиями.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============ МОИ ВАКАНСИИ ============
@router.message(F.text == "📊 Мои вакансии")
async def my_vacancies(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != "employer":
        await message.answer("❌ Только для работодателей")
        return

    vacancies = await get_vacancies_by_employer(user.id)
    if not vacancies:
        await message.answer("📭 У вас пока нет вакансий.\nСоздайте новую через кнопку ➕ Создать вакансию")
        return

    text = "📊 <b>Ваши вакансии:</b>\n\n"
    for vac in vacancies:
        status_ru = {
            "active": "✅ Активна",
            "filled": "🔒 Закрыта",
            "expired": "⏰ Истекла",
            "pending_payment": "💰 Ожидает оплаты"
        }.get(vac.status, vac.status)

        text += f"<b>{vac.id}</b> — {vac.title}\n"
        text += f"   Статус: {status_ru}\n"
        text += f"   Откликов: {vac.applications_count}\n\n"

    await message.answer(text, parse_mode="HTML")


# ============ ВСЕ ОТКЛИКИ ============
@router.message(F.text == "📋 Все отклики")
async def employer_applications(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != "employer":
        await message.answer("❌ Только для работодателей")
        return

    vacancies = await get_vacancies_by_employer(user.id)
    if not vacancies:
        await message.answer("📭 У вас нет вакансий")
        return

    text = "👥 <b>Все отклики на ваши вакансии:</b>\n\n"
    has_applications = False

    for vac in vacancies:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Application).where(Application.vacancy_id == vac.id)
            )
            apps = result.scalars().all()

        if apps:
            has_applications = True
            text += f"📌 <b>{vac.title}</b> (ID: {vac.id})\n"
            for app in apps:
                # ✅ ПРАВИЛЬНО получаем соискателя по его внутреннему ID
                async with async_session_maker() as session:
                    worker_result = await session.execute(
                        select(User).where(User.id == app.worker_id)
                    )
                    worker = worker_result.scalar_one_or_none()

                if worker:
                    worker_name = worker.first_name or worker.username or "Без имени"
                else:
                    worker_name = "❌ Пользователь удалён"

                status_ru = {
                    "pending": "⏳ Ожидает",
                    "accepted": "✅ Принят",
                    "rejected": "❌ Отклонён"
                }.get(app.status, app.status)
                text += f"   • {worker_name} — {status_ru} (отклик #{app.id})\n"
            text += "\n"

    if not has_applications:
        await message.answer("📭 Пока нет откликов на ваши вакансии")
    else:
        await message.answer(text, parse_mode="HTML")


# ============ ОПЛАТИТЬ ВАКАНСИЮ ============
@router.message(F.text == "💰 Оплатить вакансию")
async def pay_vacancy(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != "employer":
        await message.answer("❌ Только для работодателей")
        return

    vacancies = await get_vacancies_by_employer(user.id)
    pending_vacancies = [v for v in vacancies if v.status == "pending_payment"]

    if not pending_vacancies:
        await message.answer("✅ У вас нет вакансий, ожидающих оплаты")
        return

    text = "💰 <b>Вакансии, ожидающие оплаты:</b>\n\n"
    for vac in pending_vacancies:
        text += f"📌 ID: {vac.id} — {vac.title}\n"
        text += f"   Стоимость: 100 руб\n"
        text += f"   Оплатите на карту: <code>{YOUR_CARD_NUMBER}</code>\n"
        text += f"   Комментарий: <code>VAC_{vac.id}</code>\n\n"

    await message.answer(text, parse_mode="HTML")


# ============ УДАЛЕНИЕ ВАКАНСИИ ============
@router.message(F.text == "❌ Удалить вакансию")
async def delete_vacancy_menu(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or user.role != "employer":
        await message.answer("❌ Только для работодателей")
        return

    vacancies = await get_vacancies_by_employer(user.id)
    active_vacancies = [v for v in vacancies if v.status == "active"]

    if not active_vacancies:
        await message.answer("📭 У вас нет активных вакансий для удаления")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for vac in active_vacancies:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"❌ {vac.title}", callback_data=f"del_vac_{vac.id}")
        ])

    await message.answer(
        "🗑 <b>Выберите вакансию для удаления:</b>\n\n"
        "После удаления вакансия перестанет быть видна соискателям.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("del_vac_"))
async def confirm_delete_vacancy(callback: CallbackQuery):
    vacancy_id = int(callback.data.split("_")[2])
    vacancy = await get_vacancy_by_id(vacancy_id)

    if not vacancy:
        await callback.answer("❌ Вакансия не найдена", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del_{vacancy_id}"),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel_del")
        ]
    ])

    await callback.message.edit_text(
        f"⚠️ <b>Вы уверены, что хотите удалить вакансию?</b>\n\n"
        f"📌 {vacancy.title}\n\n"
        f"После удаления восстановить будет нельзя.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_del_"))
async def delete_vacancy(callback: CallbackQuery):
    vacancy_id = int(callback.data.split("_")[2])

    async with async_session_maker() as session:
        await session.execute(
            update(Vacancy).where(Vacancy.id == vacancy_id).values(
                status="expired",
                is_active=False
            )
        )
        await session.commit()

    await callback.message.edit_text(
        f"✅ <b>Вакансия удалена!</b>\n\n"
        f"Она больше не видна соискателям.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_del")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text("✅ Удаление отменено")
    await callback.answer()


# ============ УДАЛЕНИЕ ПРОФИЛЯ РАБОТОДАТЕЛЯ ============
@router.message(F.text == "🗑 Удалить профиль")
async def delete_employer_profile_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚠️ ДА, УДАЛИТЬ", callback_data="confirm_delete_employer_profile"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_employer_profile")
        ]
    ])

    await message.answer(
        "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        "Вы собираетесь удалить свой профиль работодателя.\n\n"
        "❌ Все ваши вакансии будут удалены\n"
        "❌ Все отклики на ваши вакансии будут удалены\n"
        "❌ Вы потеряете доступ к истории\n\n"
        "<i>После удаления вы сможете зарегистрироваться заново.</i>\n\n"
        "Вы уверены?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_delete_employer_profile")
async def confirm_delete_employer_profile(callback: CallbackQuery):
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Профиль не найден")
        await callback.answer()
        return

    async with async_session_maker() as session:
        # Получаем ID всех вакансий работодателя
        result = await session.execute(
            select(Vacancy.id).where(Vacancy.employer_id == user.id)
        )
        vacancy_ids = [vac_id for vac_id in result.scalars().all()]

        # Удаляем отклики на вакансии работодателя
        if vacancy_ids:
            await session.execute(
                delete(Application).where(Application.vacancy_id.in_(vacancy_ids))
            )

        # Удаляем вакансии работодателя
        await session.execute(delete(Vacancy).where(Vacancy.employer_id == user.id))

        # Удаляем платежи
        await session.execute(delete(Payment).where(Payment.user_id == user.id))

        # Удаляем подписки
        await session.execute(delete(Subscription).where(Subscription.user_id == user.id))

        # Удаляем профиль
        await session.execute(delete(User).where(User.telegram_id == callback.from_user.id))

        await session.commit()

    await callback.message.edit_text(
        "✅ <b>Ваш профиль работодателя удалён!</b>\n\n"
        "Отправьте /start, чтобы зарегистрироваться заново.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_delete_employer_profile")
async def cancel_delete_employer_profile(callback: CallbackQuery):
    await callback.message.edit_text("✅ Удаление профиля отменено")
    await callback.answer()


# ============ ПРИЛОЖЕНИЕ ============
@router.message(F.text == "📱 Приложение")
async def open_app(message: Message):
    from bot.handlers.webapp import open_webapp
    await open_webapp(message)


# ============ О БОТЕ ============
@router.message(F.text == "ℹ️ О боте")
async def about_bot_employer(message: Message):
    await message.answer(
        "🤖 <b>JobBot v2.0</b>\n\n"
        "Платформа для поиска работы и сотрудников.\n"
        "Работодатели размещают вакансии за 400 руб.\n"
        "Соискатели находят работу бесплатно.\n\n"
        "📞 По вопросам: @ваш_чат_поддержки",
        parse_mode="HTML"
    )