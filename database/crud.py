from sqlalchemy import select, update
from database.engine import async_session_maker
from database.models import User, Vacancy, Application, Payment, VacancyStatus, PaymentStatus, WorkType
import datetime
from typing import Optional, List

async def create_user(telegram_id: int, role: str, first_name: str = None, username: str = None) -> User:
    async with async_session_maker() as session:
        user = User(telegram_id=telegram_id, role=role, first_name=first_name, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

async def update_user(telegram_id: int, **kwargs) -> Optional[User]:
    async with async_session_maker() as session:
        await session.execute(update(User).where(User.telegram_id == telegram_id).values(**kwargs))
        await session.commit()
        return await get_user_by_telegram_id(telegram_id)

async def create_vacancy(employer_id: int, title: str, description: str, work_type: str,
                         location_city: str = None, location_address: str = None,
                         salary_min: float = None, salary_max: float = None,
                         salary_text: str = None, requirements: str = None, responsibilities: str = None) -> Vacancy:
    async with async_session_maker() as session:
        vacancy = Vacancy(
            employer_id=employer_id, title=title, description=description,
            work_type=WorkType(work_type), location_city=location_city, location_address=location_address,
            salary_min=salary_min, salary_max=salary_max, salary_text=salary_text,
            requirements=requirements, responsibilities=responsibilities,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=30),
            status=VacancyStatus.PENDING_PAYMENT
        )
        session.add(vacancy)
        await session.commit()
        await session.refresh(vacancy)
        return vacancy

async def get_vacancy_by_id(vacancy_id: int) -> Optional[Vacancy]:
    async with async_session_maker() as session:
        result = await session.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
        return result.scalar_one_or_none()

async def get_vacancies_by_employer(employer_id: int) -> List[Vacancy]:
    async with async_session_maker() as session:
        result = await session.execute(select(Vacancy).where(Vacancy.employer_id == employer_id))
        return result.scalars().all()

async def get_active_vacancies() -> List[Vacancy]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Vacancy).where(Vacancy.status == VacancyStatus.ACTIVE,
                                  Vacancy.expires_at > datetime.datetime.utcnow())
            .order_by(Vacancy.created_at.desc())
        )
        return result.scalars().all()

async def activate_vacancy(vacancy_id: int) -> bool:
    async with async_session_maker() as session:
        await session.execute(update(Vacancy).where(Vacancy.id == vacancy_id).values(status=VacancyStatus.ACTIVE))
        await session.commit()
        return True

async def create_application(vacancy_id: int, worker_id: int) -> Application:
    async with async_session_maker() as session:
        app = Application(vacancy_id=vacancy_id, worker_id=worker_id, status="pending")
        session.add(app)
        await session.execute(update(Vacancy).where(Vacancy.id == vacancy_id).values(applications_count=Vacancy.applications_count + 1))
        await session.commit()
        await session.refresh(app)
        return app

async def create_payment(user_id: int, amount: float, payment_id: str, vacancy_id: int = None) -> Payment:
    async with async_session_maker() as session:
        payment = Payment(user_id=user_id, amount=amount, payment_id=payment_id, vacancy_id=vacancy_id)
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment

async def update_payment_status(payment_id: str, status: str):
    async with async_session_maker() as session:
        await session.execute(update(Payment).where(Payment.payment_id == payment_id).values(
            status=PaymentStatus.SUCCESS, paid_at=datetime.datetime.utcnow()))
        await session.commit()