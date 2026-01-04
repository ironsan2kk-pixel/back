"""
LoggingMiddleware - логирование всех запросов
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования входящих событий."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        if isinstance(event, Message):
            user = event.from_user
            logger.info(
                f"[MSG] User {user.id} (@{user.username}): {event.text[:50] if event.text else '[no text]'}"
            )
        
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            logger.info(
                f"[CB] User {user.id} (@{user.username}): {event.data}"
            )
        
        return await handler(event, data)
