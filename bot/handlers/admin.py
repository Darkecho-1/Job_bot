from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database.crud import get_user_by_telegram_id, get_vacancy_by_id, activate_vacancy
from database.engine import async_session_maker
from database.models import User, Vacancy, Application, Payment, PaymentTransaction, UserActivityLog, Tariff, \
    Subscription
from sqlalchemy import update, delete, select, func
import os
import csv
import io

router = Router()

OWNER_ID = int(os.getenv("ADMIN_IDS", "1138716848"))


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


# ============ ГЛАВНАЯ АДМИН-ПАНЕЛЬ ============
async def show_admin_panel(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_menu")],
        [InlineKeyboardButton(text="📌 Вакансии", callback_data="admin_vacancies_menu")],
        [InlineKeyboardButton(text="💰 Финансы", callback_data="admin_finance")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings_menu")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast_menu")],
        [InlineKeyboardButton(text="📋 Логи", callback_data="admin_logs_menu")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")]
    ])

    await callback.message.edit_text(
        "👑 <b>АДМИН ПАНЕЛЬ</b>\n\n"
        "Добро пожаловать, владелец бота!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


async def show_admin_panel_from_message(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_menu")],
        [InlineKeyboardButton(text="📌 Вакансии", callback_data="admin_vacancies_menu")],
        [InlineKeyboardButton(text="💰 Финансы", callback_data="admin_finance")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings_menu")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast_menu")],
        [InlineKeyboardButton(text="📋 Логи", callback_data="admin_logs_menu")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")]
    ])
    await message.answer(
        "👑 <b>АДМИН ПАНЕЛЬ</b>\n\n"
        "Добро пожаловать, владелец бота!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ У вас нет доступа")
        return
    await show_admin_panel_from_message(message)


async def show_with_back_button(callback: CallbackQuery, text: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ============ 1. СТАТИСТИКА ============
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session_maker() as session:
        total_users = await session.execute(select(func.count()).select_from(User))
        total_users = total_users.scalar()
        total_vacancies = await session.execute(select(func.count()).select_from(Vacancy))
        total_vacancies = total_vacancies.scalar()
        active_vacancies = await session.execute(
            select(func.count()).select_from(Vacancy).where(Vacancy.status == "active"))
        active_vacancies = active_vacancies.scalar()
        total_applications = await session.execute(select(func.count()).select_from(Application))
        total_applications = total_applications.scalar()

    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"📌 Вакансий: {total_vacancies}\n"
        f"✅ Активных вакансий: {active_vacancies}\n"
        f"📋 Откликов: {total_applications}"
    )
    await show_with_back_button(callback, text)


# ============ 2. ПОЛЬЗОВАТЕЛИ ============
@router.callback_query(F.data == "admin_users_menu")
async def admin_users_menu(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session_maker() as session:
        result = await session.execute(select(User).order_by(User.id.desc()).limit(50))
        users = result.scalars().all()

    if not users:
        await show_with_back_button(callback, "👥 <b>Пользователи</b>\n\n📭 Нет пользователей")
        return

    text = "👥 <b>Последние 50 пользователей:</b>\n\n"
    for user in users:
        ban_status = "🚫" if user.is_banned else "✅"
        text += f"{ban_status} ID: {user.telegram_id} | {user.first_name or user.username or 'Без имени'} | {user.role}\n"

    await show_with_back_button(callback, text)


# ============ 3. ВАКАНСИИ ============
@router.callback_query(F.data == "admin_vacancies_menu")
async def admin_vacancies_menu(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session_maker() as session:
        vacancies = await session.execute(select(Vacancy).order_by(Vacancy.created_at.desc()).limit(30))
        vacancies = vacancies.scalars().all()

    if not vacancies:
        await show_with_back_button(callback, "📌 <b>Вакансии</b>\n\n📭 Нет вакансий")
        return

    text = "📌 <b>Последние 30 вакансий:</b>\n\n"
    for vac in vacancies:
        status_ru = {
            "active": "✅ Активна",
            "pending_payment": "💰 Ожидает оплаты",
            "expired": "⏰ Истекла",
            "filled": "🔒 Закрыта"
        }.get(vac.status, vac.status)
        text += f"• {vac.title} (ID: {vac.id}) — {status_ru}\n"

    await show_with_back_button(callback, text)


# ============ 4. ФИНАНСЫ ============
@router.callback_query(F.data == "admin_finance")
async def admin_finance(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session_maker() as session:
        total = await session.execute(select(func.sum(Payment.amount)).where(Payment.status == "success"))
        total = total.scalar() or 0

        total_subs = await session.execute(
            select(func.count()).select_from(Subscription).where(Subscription.is_active == True))
        total_subs = total_subs.scalar() or 0

    text = (
        f"💰 <b>Финансы</b>\n\n"
        f"Общая выручка: {total} руб.\n"
        f"Активных подписок: {total_subs}"
    )
    await show_with_back_button(callback, text)


# ============ 5. НАСТРОЙКИ ============
@router.callback_query(F.data == "admin_settings_menu")
async def admin_settings_menu(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    current_price = os.getenv("VACANCY_PRICE_NORMAL", 400)
    text = (
        f"⚙️ <b>Настройки бота</b>\n\n"
        f"💰 Стоимость вакансии: {current_price} руб.\n\n"
        f"📝 Для изменения цены используйте команду:\n"
        f"<code>/set_price НОВАЯ_ЦЕНА</code>\n\n"
        f"Пример: <code>/set_price 500</code>"
    )
    await show_with_back_button(callback, text)


@router.message(Command("set_price"))
async def set_price(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ У вас нет прав")
        return
    try:
        new_price = float(message.text.split()[1])
        with open(".env", "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(".env", "w", encoding="utf-8") as f:
            for line in lines:
                if line.startswith("VACANCY_PRICE_NORMAL"):
                    f.write(f"VACANCY_PRICE_NORMAL={new_price}\n")
                else:
                    f.write(line)
        await message.answer(f"✅ Цена обновлена: {new_price} руб.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}\nИспользование: /set_price 500")


# ============ 6. РАССЫЛКА ============
@router.callback_query(F.data == "admin_broadcast_menu")
async def admin_broadcast_menu(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "📨 <b>Рассылка сообщений</b>\n\n"
        "Введите команду:\n"
        "<code>/broadcast ТЕКСТ_СООБЩЕНИЯ</code>\n\n"
        "Пример: <code>/broadcast Уважаемые пользователи! Бот обновлён!</code>\n\n"
        "⚠️ Сообщение получит ВСЕ пользователи бота.\n\n"
        "После выполнения команды вернитесь в админ-панель через /admin",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("broadcast"))
async def broadcast(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ У вас нет прав")
        return

    try:
        broadcast_text = message.text.split(maxsplit=1)[1]
    except IndexError:
        await message.answer("❌ Использование: /broadcast ТЕКСТ")
        return

    async with async_session_maker() as session:
        result = await session.execute(select(User.telegram_id))
        users = result.scalars().all()

    success = 0
    fail = 0

    status_msg = await message.answer(f"📨 Начинаю рассылку {len(users)} пользователям...")

    for user_id in users:
        try:
            await message.bot.send_message(
                user_id,
                f"📢 <b>ОБЪЯВЛЕНИЕ ОТ АДМИНА</b>\n\n{broadcast_text}",
                parse_mode="HTML"
            )
            success += 1
        except Exception:
            fail += 1

    await status_msg.edit_text(f"✅ Рассылка завершена!\nУспешно: {success}\nОшибок: {fail}")


# ============ 7. ЛОГИ ============
@router.callback_query(F.data == "admin_logs_menu")
async def admin_logs_menu(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    async with async_session_maker() as session:
        logs = await session.execute(
            select(UserActivityLog).order_by(UserActivityLog.created_at.desc()).limit(20)
        )
        logs = logs.scalars().all()

    if not logs:
        await show_with_back_button(callback, "📋 <b>Логи</b>\n\n📭 Нет записей")
        return

    text = "📋 <b>Последние 20 действий:</b>\n\n"
    for log in logs:
        user = await get_user_by_telegram_id(log.user_id)
        user_name = user.first_name or user.username or str(log.user_id)
        text += f"• {user_name} — {log.action} — {log.created_at.strftime('%d.%m.%Y %H:%M')}\n"

    await show_with_back_button(callback, text)


# ============ НАВИГАЦИЯ ============
@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await show_admin_panel(callback)


@router.callback_query(F.data == "admin_refresh")
async def admin_refresh(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await show_admin_panel(callback)


# ============ КОМАНДЫ АДМИНА ============
@router.message(Command("confirm"))
async def confirm_vacancy(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ У вас нет прав")
        return
    try:
        vacancy_id = int(message.text.split()[1])
    except:
        await message.answer("❌ Использование: /confirm <ID>")
        return

    vacancy = await get_vacancy_by_id(vacancy_id)
    if not vacancy:
        await message.answer("❌ Вакансия не найдена")
        return

    await activate_vacancy(vacancy_id)
    await message.answer(f"✅ Вакансия #{vacancy_id} активирована!")


@router.message(Command("export_users"))
async def export_users_csv(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ У вас нет прав")
        return

    async with async_session_maker() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Telegram ID", "Имя", "Телефон", "Город", "Роль"])
        for user in users:
            writer.writerow([
                user.telegram_id,
                user.first_name or "—",
                user.phone or "—",
                user.city or "—",
                user.role
            ])

    file = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    await message.answer_document(document=file, filename="users_export.csv")