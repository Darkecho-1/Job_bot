from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.crud import get_user_by_telegram_id, get_vacancy_by_id
from database.engine import async_session_maker
from database.models import User, Vacancy, Application, Subscription, Tariff
from sqlalchemy import select, func
import json

router = Router()


@router.message(Command("get_app_data"))
async def send_app_data(message: Message):
    """Отправляет реальные данные пользователя для мини-приложения"""
    user = await get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer(json.dumps({"error": "Пользователь не найден"}))
        return

    # Получаем данные из базы
    async with async_session_maker() as session:
        # Активные вакансии
        vacancies_result = await session.execute(
            select(Vacancy).where(Vacancy.status == "active").order_by(Vacancy.created_at.desc()).limit(20)
        )
        vacancies = vacancies_result.scalars().all()

        # Отклики пользователя
        apps_result = await session.execute(
            select(Application).where(Application.worker_id == user.id)
        )
        applications = apps_result.scalars().all()

        # Подписка пользователя
        sub_result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.is_active == True
            )
        )
        subscription = sub_result.scalar_one_or_none()

        # Название тарифа
        tariff_name = None
        if subscription:
            tariff = await session.execute(
                select(Tariff).where(Tariff.id == subscription.tariff_id)
            )
            tariff_obj = tariff.scalar_one_or_none()
            tariff_name = tariff_obj.name if tariff_obj else "Активна"

    # Формируем данные
    data = {
        "user": {
            "telegram_id": user.telegram_id,
            "first_name": user.first_name or "Не указано",
            "last_name": user.last_name or "",
            "phone": user.phone or "Не указан",
            "city": user.city or "Не указан",
            "role": user.role,
            "is_registered": user.is_registered,
            "is_banned": user.is_banned
        },
        "vacancies": [
            {
                "id": v.id,
                "title": v.title,
                "description": v.description[:150] + "..." if len(v.description) > 150 else v.description,
                "salary": v.salary_text or f"{v.salary_min} - {v.salary_max} руб.",
                "city": v.location_city or "Удаленно",
                "type": v.work_type,
                "employer_id": v.employer_id
            }
            for v in vacancies
        ],
        "applications": [
            {
                "id": app.id,
                "vacancy_id": app.vacancy_id,
                "status": app.status,
                "created_at": app.created_at.strftime("%d.%m.%Y %H:%M")
            }
            for app in applications
        ],
        "subscription": {
            "is_active": subscription is not None,
            "name": tariff_name,
            "expires_at": subscription.expires_at.strftime("%d.%m.%Y") if subscription else None
        },
        "stats": {
            "applications_count": len(applications),
            "vacancies_count": len(vacancies)
        }
    }

    await message.answer(json.dumps(data, ensure_ascii=False))