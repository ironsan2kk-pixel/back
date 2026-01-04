"""
DatabaseMiddleware - сессия БД для каждого запроса
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.database import async_session


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для предоставления сессии БД в каждый handler."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        if async_session is None:
            # БД не инициализирована
            return await handler(event, data)
        
        async with async_session() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
