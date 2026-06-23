from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.crud import get_user_by_telegram_id

class RoleCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable, event: Message, data: Dict[str, Any]) -> Any:
        if isinstance(event, CallbackQuery):
            user = await get_user_by_telegram_id(event.from_user.id)
            if user and user.is_banned:
                await event.answer("🚫 Ваш аккаунт заблокирован", show_alert=True)
                return
        return await handler(event, data)