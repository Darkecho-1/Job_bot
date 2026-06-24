from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import os

from bot.handlers import (
    start, registration, admin, employer_menu, worker_menu,
    vacancy_creation, vacancy_matching, payments, subscription
)
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.activity_logger import ActivityLoggerMiddleware
from bot.middlewares.role_check import RoleCheckMiddleware
from bot.handlers import webapp
from bot.handlers import webapp_api
from bot.handlers import webapp_data


async def setup_dispatcher():
    storage = MemoryStorage()

    bot = Bot(
        token=os.getenv("BOT_TOKEN"),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=storage)

    # Middlewares
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(ActivityLoggerMiddleware())
    dp.callback_query.middleware(ActivityLoggerMiddleware())
    dp.message.middleware(RoleCheckMiddleware())
    dp.callback_query.middleware(RoleCheckMiddleware())

    # Роутеры
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(admin.router)
    dp.include_router(employer_menu.router)
    dp.include_router(worker_menu.router)
    dp.include_router(vacancy_creation.router)
    dp.include_router(vacancy_matching.router)
    dp.include_router(payments.router)
    dp.include_router(subscription.router)
    dp.include_router(webapp.router)
    dp.include_router(webapp_api.router)
    dp.include_router(webapp_data.router)

    return dp, bot