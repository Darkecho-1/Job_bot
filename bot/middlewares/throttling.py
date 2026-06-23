from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
import time


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        super().__init__()
        self.rate_limit = rate_limit
        self.user_last_request = {}

    async def __call__(self, handler: Callable, event: Message, data: Dict[str, Any]) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        if current_time - self.user_last_request.get(user_id, 0) < self.rate_limit:
            return
        self.user_last_request[user_id] = current_time
        return await handler(event, data)