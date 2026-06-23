from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.engine import async_session_maker

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: Message, data: Dict[str, Any]) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)