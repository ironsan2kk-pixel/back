"""
I18nMiddleware - интернационализация
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from config import settings


class I18nMiddleware(BaseMiddleware):
    """Middleware для определения языка пользователя."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        
        # Определяем язык пользователя
        lang = settings.DEFAULT_LANGUAGE
        
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user:
            # Можно получить язык из БД если есть session
            session = data.get("session")
            if session:
                try:
                    from database.crud import UserCRUD
                    db_user = await UserCRUD.get_by_telegram_id(session, user.id)
                    if db_user and db_user.language:
                        lang = db_user.language
                except:
                    pass
            
            # Fallback на язык из Telegram
            if not lang and user.language_code:
                lang = user.language_code[:2]
        
        # Добавляем язык в data
        data["lang"] = lang
        data["_"] = lambda key, **kw: self.get_text(key, lang, **kw)
        
        return await handler(event, data)
    
    def get_text(self, key: str, lang: str, **kwargs) -> str:
        """Получение текста по ключу."""
        try:
            from utils.i18n import get_text
            return get_text(key, lang, **kwargs)
        except:
            return key
