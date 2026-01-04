"""
ThrottlingMiddleware - защита от спама
"""

import asyncio
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов."""
    
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.user_last_request: Dict[int, float] = {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        
        if user:
            user_id = user.id
            current_time = asyncio.get_event_loop().time()
            last_request = self.user_last_request.get(user_id, 0)
            
            if current_time - last_request < self.rate_limit:
                # Слишком частые запросы - пропускаем
                return None
            
            self.user_last_request[user_id] = current_time
        
        return await handler(event, data)
