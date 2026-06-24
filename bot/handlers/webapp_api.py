from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from database.crud import get_user_by_telegram_id, get_vacancies_by_employer, get_vacancy_by_id
from database.engine import async_session_maker
from database.models import User, Vacancy, Application, Tariff, Subscription
from sqlalchemy import select, func
import json

router = Router()

@router.message(Command("app_data"))
async def send_app_data(message: Message):
    """Отправляет данные для мини-приложения"""
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(json.dumps({"error": "Пользователь не найден"}))
        return

    # Получаем вакансии
    async with async_session_maker() as session:
        # Активные вакансии
        vacancies_result = await session.execute(
            select(Vacancy).where(Vacancy.status == "active").order_by(Vacancy.created_at.desc()).limit(10)
        )
        vacancies = vacancies_result.scalars().all()

        # Количество откликов
        apps_count = await session.execute(
            select(func.count()).select_from(Application).where(Application.worker_id == user.id)
        )
        apps_count = apps_count.scalar() or 0

        # Подписка
        subscription = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.is_active == True
            )
        )
        subscription = subscription.scalar_one_or_none()

    # Формируем данные для приложения
    data = {
        "user": {
            "name": user.first_name or "Пользователь",
            "phone": user.phone or "Не указан",
            "city": user.city or "Не указан",
            "role": user.role,
            "is_banned": user.is_banned
        },
        "vacancies": [
            {
                "id": v.id,
                "title": v.title,
                "description": v.description[:100] + "..." if len(v.description) > 100 else v.description,
                "salary": v.salary_text or f"{v.salary_min} - {v.salary_max} руб.",
                "city": v.location_city or "Удаленно",
                "type": v.work_type,
                "employer": (await get_user_by_telegram_id(v.employer_id)).first_name or "Работодатель"
            }
            for v in vacancies
        ],
        "stats": {
            "applications": apps_count,
            "has_subscription": subscription is not None,
            "subscription_name": subscription.tariff_id if subscription else None
        }
    }

    await message.answer(json.dumps(data, ensure_ascii=False))