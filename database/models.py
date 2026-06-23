from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, Enum, BigInteger
from database.engine import Base
import datetime
import enum

class UserRole(str, enum.Enum):
    WORKER = "worker"
    EMPLOYER = "employer"

class WorkType(str, enum.Enum):
    ONLINE = "online"
    PHYSICAL = "physical"
    BOTH = "both"

class VacancyStatus(str, enum.Enum):
    ACTIVE = "active"
    FILLED = "filled"
    EXPIRED = "expired"
    PENDING_PAYMENT = "pending_payment"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    patronymic = Column(String(100))
    birth_date = Column(DateTime)
    phone = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)
    city = Column(String(100))
    district = Column(String(100))
    preferred_work_type = Column(Enum(WorkType), default=WorkType.BOTH)
    is_registered = Column(Boolean, default=False)
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)
    balance = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)
    total_spent = Column(Float, default=0.0)
    is_banned = Column(Boolean, default=False)

class Vacancy(Base):
    __tablename__ = "vacancies"
    id = Column(Integer, primary_key=True)
    employer_id = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    work_type = Column(Enum(WorkType), nullable=False)
    location_city = Column(String(100))
    location_address = Column(String(300))
    salary_min = Column(Float)
    salary_max = Column(Float)
    salary_text = Column(String(200))
    requirements = Column(Text)
    responsibilities = Column(Text)
    is_active = Column(Boolean, default=True)
    status = Column(Enum(VacancyStatus), default=VacancyStatus.PENDING_PAYMENT)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)
    views_count = Column(Integer, default=0)
    applications_count = Column(Integer, default=0)

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    vacancy_id = Column(Integer, nullable=False)
    worker_id = Column(Integer, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_id = Column(String(100))
    vacancy_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    paid_at = Column(DateTime)

class Tariff(Base):
    __tablename__ = "tariffs"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    description = Column(Text)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    tariff_id = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    purpose = Column(String(100))
    payment_id = Column(String(100))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    paid_at = Column(DateTime)

class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    action = Column(String(100))
    vacancy_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)