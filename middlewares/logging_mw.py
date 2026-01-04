"""
═══════════════════════════════════════════════════════════════════════════════
📝 LOGGING MIDDLEWARE — ЛОГИРОВАНИЕ ДЕЙСТВИЙ
═══════════════════════════════════════════════════════════════════════════════
Логирование всех действий пользователей и ботов.
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import time
from datetime import datetime
from typing import Callable, Dict, Any, Awaitable, Optional

from aiogram import BaseMiddleware
from aiogram.types import (
    TelegramObject, Update, Message, CallbackQuery
)

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования действий.
    
    Логирует:
    - Входящие сообщения
    - Callback запросы
    - Время обработки
    """
    
    def __init__(
        self,
        log_level: int = logging.INFO,
        log_messages: bool = True,
        log_callbacks: bool = True,
        log_processing_time: bool = True,
    ):
        """
        Инициализация middleware.
        
        Args:
            log_level: Уровень логирования
            log_messages: Логировать сообщения
            log_callbacks: Логировать callback
            log_processing_time: Логировать время обработки
        """
        super().__init__()
        self.log_level = log_level
        self.log_messages = log_messages
        self.log_callbacks = log_callbacks
        self.log_processing_time = log_processing_time
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события."""
        start_time = time.time()
        
        # Логируем входящее событие
        self._log_incoming(event)
        
        try:
            result = await handler(event, data)
            
            # Логируем успешную обработку
            if self.log_processing_time:
                elapsed = time.time() - start_time
                self._log_success(event, elapsed)
            
            return result
            
        except Exception as e:
            # Логируем ошибку
            elapsed = time.time() - start_time
            self._log_error(event, e, elapsed)
            raise
    
    def _log_incoming(self, event: TelegramObject) -> None:
        """Логирование входящего события."""
        if isinstance(event, Update):
            if event.message and self.log_messages:
                self._log_message(event.message)
            elif event.callback_query and self.log_callbacks:
                self._log_callback(event.callback_query)
        elif isinstance(event, Message) and self.log_messages:
            self._log_message(event)
        elif isinstance(event, CallbackQuery) and self.log_callbacks:
            self._log_callback(event)
    
    def _log_message(self, message: Message) -> None:
        """Логирование сообщения."""
        user = message.from_user
        user_info = f"{user.id}" if user else "unknown"
        
        if user and user.username:
            user_info += f" (@{user.username})"
        
        text = message.text[:50] if message.text else "[non-text]"
        if message.text and len(message.text) > 50:
            text += "..."
        
        logger.log(
            self.log_level,
            f"📩 Message from {user_info}: {text}"
        )
    
    def _log_callback(self, callback: CallbackQuery) -> None:
        """Логирование callback."""
        user = callback.from_user
        user_info = f"{user.id}" if user else "unknown"
        
        if user and user.username:
            user_info += f" (@{user.username})"
        
        data = callback.data[:30] if callback.data else "[empty]"
        if callback.data and len(callback.data) > 30:
            data += "..."
        
        logger.log(
            self.log_level,
            f"🔘 Callback from {user_info}: {data}"
        )
    
    def _log_success(self, event: TelegramObject, elapsed: float) -> None:
        """Логирование успешной обработки."""
        logger.debug(f"✅ Processed in {elapsed:.3f}s")
    
    def _log_error(
        self,
        event: TelegramObject,
        error: Exception,
        elapsed: float,
    ) -> None:
        """Логирование ошибки."""
        logger.error(
            f"❌ Error after {elapsed:.3f}s: {type(error).__name__}: {error}"
        )


class ActivityLogMiddleware(BaseMiddleware):
    """
    Middleware для записи активности в БД.
    
    Записывает все действия пользователей в таблицу activity_log.
    """
    
    def __init__(
        self,
        get_session: Callable,
        log_messages: bool = True,
        log_callbacks: bool = True,
        log_commands: bool = True,
    ):
        """
        Инициализация middleware.
        
        Args:
            get_session: Функция получения сессии БД
            log_messages: Записывать сообщения
            log_callbacks: Записывать callback
            log_commands: Записывать команды
        """
        super().__init__()
        self.get_session = get_session
        self.log_messages = log_messages
        self.log_callbacks = log_callbacks
        self.log_commands = log_commands
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события."""
        # Записываем активность
        await self._log_activity(event, data)
        
        return await handler(event, data)
    
    async def _log_activity(
        self,
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> None:
        """Запись активности в БД."""
        try:
            from database.crud import ActivityLogCRUD
            
            user_id = data.get("user_id")
            if not user_id:
                return
            
            action = None
            details = None
            
            if isinstance(event, Update):
                if event.message:
                    if event.message.text and event.message.text.startswith("/"):
                        if self.log_commands:
                            action = "command"
                            details = event.message.text.split()[0]
                    elif self.log_messages:
                        action = "message"
                        details = event.message.content_type
                elif event.callback_query and self.log_callbacks:
                    action = "callback"
                    details = event.callback_query.data
            elif isinstance(event, Message):
                if event.text and event.text.startswith("/"):
                    if self.log_commands:
                        action = "command"
                        details = event.text.split()[0]
                elif self.log_messages:
                    action = "message"
                    details = event.content_type
            elif isinstance(event, CallbackQuery) and self.log_callbacks:
                action = "callback"
                details = event.data
            
            if action:
                with self.get_session() as session:
                    ActivityLogCRUD.create(
                        session,
                        user_id=user_id,
                        action=action,
                        details=details[:255] if details else None,
                    )
                    
        except Exception as e:
            logger.debug(f"Error logging activity: {e}")


class StatsMiddleware(BaseMiddleware):
    """
    Middleware для сбора статистики.
    
    Подсчитывает количество запросов, время ответа и т.д.
    """
    
    def __init__(self, get_session: Optional[Callable] = None):
        """
        Инициализация middleware.
        
        Args:
            get_session: Функция получения сессии (для записи в БД)
        """
        super().__init__()
        self.get_session = get_session
        
        # Счётчики в памяти
        self.stats = {
            "total_requests": 0,
            "messages": 0,
            "callbacks": 0,
            "commands": 0,
            "errors": 0,
            "total_processing_time": 0.0,
        }
        
        self._today_date: Optional[str] = None
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события."""
        start_time = time.time()
        
        # Проверяем смену дня
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._today_date != today:
            await self._save_daily_stats()
            self._reset_stats()
            self._today_date = today
        
        # Обновляем счётчики
        self.stats["total_requests"] += 1
        self._update_type_counter(event)
        
        try:
            result = await handler(event, data)
            
            elapsed = time.time() - start_time
            self.stats["total_processing_time"] += elapsed
            
            return result
            
        except Exception:
            self.stats["errors"] += 1
            raise
    
    def _update_type_counter(self, event: TelegramObject) -> None:
        """Обновление счётчика по типу события."""
        if isinstance(event, Update):
            if event.message:
                if event.message.text and event.message.text.startswith("/"):
                    self.stats["commands"] += 1
                else:
                    self.stats["messages"] += 1
            elif event.callback_query:
                self.stats["callbacks"] += 1
        elif isinstance(event, Message):
            if event.text and event.text.startswith("/"):
                self.stats["commands"] += 1
            else:
                self.stats["messages"] += 1
        elif isinstance(event, CallbackQuery):
            self.stats["callbacks"] += 1
    
    def _reset_stats(self) -> None:
        """Сброс статистики."""
        self.stats = {
            "total_requests": 0,
            "messages": 0,
            "callbacks": 0,
            "commands": 0,
            "errors": 0,
            "total_processing_time": 0.0,
        }
    
    async def _save_daily_stats(self) -> None:
        """Сохранение дневной статистики в БД."""
        if not self.get_session or not self._today_date:
            return
        
        if self.stats["total_requests"] == 0:
            return
        
        try:
            from database.crud import DailyStatsCRUD
            
            with self.get_session() as session:
                # Здесь можно сохранить статистику
                # DailyStatsCRUD.update_daily(...)
                pass
                
        except Exception as e:
            logger.error(f"Error saving daily stats: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение текущей статистики."""
        avg_time = 0.0
        if self.stats["total_requests"] > 0:
            avg_time = self.stats["total_processing_time"] / self.stats["total_requests"]
        
        return {
            **self.stats,
            "average_processing_time": avg_time,
            "date": self._today_date,
        }
