from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.engine import async_session_maker
from database.models import UserActivityLog
import datetime

class ActivityLoggerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        action = "unknown"
        vacancy_id = None
        if isinstance(event, Message):
            action = "message"
        elif isinstance(event, CallbackQuery):
            action = event.data.split("_")[0] if event.data else "callback"
            if "vac_" in event.data:
                try:
                    vacancy_id = int(event.data.split("_")[2])
                except:
                    pass
        try:
            async with async_session_maker() as session:
                log = UserActivityLog(
                    user_id=event.from_user.id,
                    action=action,
                    vacancy_id=vacancy_id,
                    created_at=datetime.datetime.utcnow()
                )
                session.add(log)
                await session.commit()
        except:
            pass
        return await handler(event, data)