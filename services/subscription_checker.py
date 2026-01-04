"""
═══════════════════════════════════════════════════════════════════════════════
🔄 SUBSCRIPTION CHECKER — АВТОМАТИЧЕСКАЯ ПРОВЕРКА ПОДПИСОК
═══════════════════════════════════════════════════════════════════════════════
Фоновая задача для:
- Проверки истекших подписок
- Автоматического кика пользователей
- Уведомлений об истечении
- Статистики
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Awaitable, Dict, Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


@dataclass
class ExpiredSubscription:
    """Информация об истекшей подписке."""
    subscription_id: int
    user_id: int
    telegram_id: int
    subscription_type: str  # 'channel' или 'package'
    item_id: int
    item_name: str
    channel_ids: List[int]
    expired_at: datetime
    days_overdue: int


@dataclass
class ExpiringSubscription:
    """Информация о скоро истекающей подписке."""
    subscription_id: int
    user_id: int
    telegram_id: int
    subscription_type: str
    item_id: int
    item_name: str
    expires_at: datetime
    days_left: int


@dataclass
class CheckResult:
    """Результат проверки подписок."""
    checked_at: datetime = field(default_factory=datetime.utcnow)
    total_subscriptions: int = 0
    expired_count: int = 0
    kicked_count: int = 0
    expiring_soon_count: int = 0
    notifications_sent: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Успешна ли проверка."""
        return len(self.errors) == 0


# Типы callback функций
ExpiredCallback = Callable[[ExpiredSubscription], Awaitable[None]]
ExpiringCallback = Callable[[ExpiringSubscription], Awaitable[None]]


class SubscriptionChecker:
    """
    Сервис проверки подписок.
    
    Запускается как фоновая задача и периодически:
    1. Находит истекшие подписки
    2. Кикает пользователей из каналов
    3. Отмечает подписки как истекшие в БД
    4. Отправляет уведомления
    5. Предупреждает о скором истечении
    """
    
    def __init__(
        self,
        bot: Bot,
        get_session: Callable,
        channel_manager,  # ChannelManager
        check_interval: int = 3600,  # 1 час
        warning_days: List[int] = None,  # Дни для предупреждений
        auto_kick: bool = True,
        grace_period_hours: int = 0,  # Льготный период
    ):
        """
        Инициализация чекера.
        
        Args:
            bot: Экземпляр aiogram Bot
            get_session: Функция получения сессии БД
            channel_manager: Менеджер каналов
            check_interval: Интервал проверки в секундах
            warning_days: Дни для предупреждений [7, 3, 1]
            auto_kick: Автоматически кикать пользователей
            grace_period_hours: Льготный период после истечения
        """
        self.bot = bot
        self.get_session = get_session
        self.channel_manager = channel_manager
        self.check_interval = check_interval
        self.warning_days = warning_days or [7, 3, 1]
        self.auto_kick = auto_kick
        self.grace_period_hours = grace_period_hours
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_expired: Optional[ExpiredCallback] = None
        self._on_expiring: Optional[ExpiringCallback] = None
        
        # Последний результат
        self.last_result: Optional[CheckResult] = None
    
    def on_expired(self, callback: ExpiredCallback) -> None:
        """Установка callback для истекших подписок."""
        self._on_expired = callback
    
    def on_expiring(self, callback: ExpiringCallback) -> None:
        """Установка callback для скоро истекающих подписок."""
        self._on_expiring = callback
    
    # ═══════════════════════════════════════════════════════════════════════
    # УПРАВЛЕНИЕ ЗАДАЧЕЙ
    # ═══════════════════════════════════════════════════════════════════════
    
    async def start(self) -> None:
        """Запуск фоновой задачи."""
        if self._running:
            logger.warning("Subscription checker already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"Subscription checker started, interval: {self.check_interval}s"
        )
    
    async def stop(self) -> None:
        """Остановка фоновой задачи."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Subscription checker stopped")
    
    async def _run_loop(self) -> None:
        """Основной цикл проверки."""
        while self._running:
            try:
                result = await self.check_subscriptions()
                self.last_result = result
                
                logger.info(
                    f"Subscription check completed: "
                    f"expired={result.expired_count}, "
                    f"kicked={result.kicked_count}, "
                    f"expiring_soon={result.expiring_soon_count}"
                )
                
            except Exception as e:
                logger.error(f"Error in subscription check loop: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ПРОВЕРКА ПОДПИСОК
    # ═══════════════════════════════════════════════════════════════════════
    
    async def check_subscriptions(self) -> CheckResult:
        """
        Полная проверка подписок.
        
        Returns:
            Результат проверки
        """
        result = CheckResult()
        
        try:
            # Получаем истекшие подписки
            expired = await self._get_expired_subscriptions()
            result.expired_count = len(expired)
            
            # Обрабатываем истекшие
            for sub in expired:
                try:
                    await self._handle_expired(sub)
                    result.kicked_count += 1
                except Exception as e:
                    result.errors.append(f"Error handling expired {sub.subscription_id}: {e}")
            
            # Получаем скоро истекающие
            expiring = await self._get_expiring_subscriptions()
            result.expiring_soon_count = len(expiring)
            
            # Отправляем предупреждения
            for sub in expiring:
                try:
                    await self._handle_expiring(sub)
                    result.notifications_sent += 1
                except Exception as e:
                    result.errors.append(f"Error handling expiring {sub.subscription_id}: {e}")
            
            # Получаем общее количество активных
            result.total_subscriptions = await self._count_active_subscriptions()
            
        except Exception as e:
            result.errors.append(f"General error: {e}")
            logger.error(f"Subscription check error: {e}")
        
        return result
    
    async def check_single_user(self, user_id: int) -> Dict[str, Any]:
        """
        Проверка подписок конкретного пользователя.
        
        Args:
            user_id: ID пользователя в БД
            
        Returns:
            Результат проверки
        """
        result = {
            "user_id": user_id,
            "active": [],
            "expired": [],
            "expiring_soon": [],
        }
        
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from database.crud import UserSubscriptionCRUD
            from database.models import SubscriptionStatus
            
            with self.get_session() as session:
                subscriptions = UserSubscriptionCRUD.get_user_subscriptions(
                    session, user_id, status=SubscriptionStatus.ACTIVE
                )
                
                now = datetime.utcnow()
                
                for sub in subscriptions:
                    sub_info = {
                        "id": sub.id,
                        "type": sub.subscription_type.value,
                        "expires_at": sub.end_date.isoformat() if sub.end_date else None,
                    }
                    
                    if sub.end_date and sub.end_date < now:
                        result["expired"].append(sub_info)
                    elif sub.end_date and sub.end_date < now + timedelta(days=max(self.warning_days)):
                        days_left = (sub.end_date - now).days
                        sub_info["days_left"] = days_left
                        result["expiring_soon"].append(sub_info)
                    else:
                        result["active"].append(sub_info)
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # ВНУТРЕННИЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _get_expired_subscriptions(self) -> List[ExpiredSubscription]:
        """Получение списка истекших подписок."""
        from database.crud import UserSubscriptionCRUD, ChannelCRUD, PackageCRUD
        from database.models import SubscriptionStatus, SubscriptionType
        
        expired_list = []
        now = datetime.utcnow()
        
        # Учитываем льготный период
        check_time = now - timedelta(hours=self.grace_period_hours)
        
        with self.get_session() as session:
            # Получаем активные подписки с истекшим сроком
            subscriptions = UserSubscriptionCRUD.get_expired_active(
                session, check_time
            )
            
            for sub in subscriptions:
                try:
                    # Определяем каналы для кика
                    channel_ids = []
                    item_name = ""
                    
                    if sub.subscription_type == SubscriptionType.CHANNEL:
                        if sub.channel:
                            channel_ids = [sub.channel.telegram_id]
                            item_name = sub.channel.name_ru or sub.channel.name_en or ""
                    
                    elif sub.subscription_type == SubscriptionType.PACKAGE:
                        if sub.package:
                            item_name = sub.package.name_ru or sub.package.name_en or ""
                            # Получаем каналы пакета
                            for pc in sub.package.channels:
                                if pc.channel:
                                    channel_ids.append(pc.channel.telegram_id)
                    
                    days_overdue = (now - sub.end_date).days if sub.end_date else 0
                    
                    expired_list.append(ExpiredSubscription(
                        subscription_id=sub.id,
                        user_id=sub.user_id,
                        telegram_id=sub.user.telegram_id if sub.user else 0,
                        subscription_type=sub.subscription_type.value,
                        item_id=sub.channel_id or sub.package_id or 0,
                        item_name=item_name,
                        channel_ids=channel_ids,
                        expired_at=sub.end_date or now,
                        days_overdue=days_overdue,
                    ))
                    
                except Exception as e:
                    logger.error(f"Error processing subscription {sub.id}: {e}")
        
        return expired_list
    
    async def _get_expiring_subscriptions(self) -> List[ExpiringSubscription]:
        """Получение списка скоро истекающих подписок."""
        from database.crud import UserSubscriptionCRUD
        from database.models import SubscriptionStatus, SubscriptionType
        
        expiring_list = []
        now = datetime.utcnow()
        
        with self.get_session() as session:
            for days in self.warning_days:
                # Получаем подписки, истекающие через N дней
                target_date = now + timedelta(days=days)
                start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                subscriptions = UserSubscriptionCRUD.get_expiring_between(
                    session, start_of_day, end_of_day
                )
                
                for sub in subscriptions:
                    try:
                        item_name = ""
                        
                        if sub.subscription_type == SubscriptionType.CHANNEL and sub.channel:
                            item_name = sub.channel.name_ru or sub.channel.name_en or ""
                        elif sub.subscription_type == SubscriptionType.PACKAGE and sub.package:
                            item_name = sub.package.name_ru or sub.package.name_en or ""
                        
                        expiring_list.append(ExpiringSubscription(
                            subscription_id=sub.id,
                            user_id=sub.user_id,
                            telegram_id=sub.user.telegram_id if sub.user else 0,
                            subscription_type=sub.subscription_type.value,
                            item_id=sub.channel_id or sub.package_id or 0,
                            item_name=item_name,
                            expires_at=sub.end_date,
                            days_left=days,
                        ))
                        
                    except Exception as e:
                        logger.error(f"Error processing expiring subscription {sub.id}: {e}")
        
        return expiring_list
    
    async def _handle_expired(self, sub: ExpiredSubscription) -> None:
        """Обработка истекшей подписки."""
        from database.crud import UserSubscriptionCRUD
        from database.models import SubscriptionStatus
        
        # Кикаем из каналов
        if self.auto_kick and sub.channel_ids:
            await self.channel_manager.kick_from_multiple_channels(
                channel_ids=sub.channel_ids,
                user_id=sub.telegram_id,
            )
        
        # Обновляем статус в БД
        with self.get_session() as session:
            UserSubscriptionCRUD.update_status(
                session, sub.subscription_id, SubscriptionStatus.EXPIRED
            )
        
        # Вызываем callback
        if self._on_expired:
            await self._on_expired(sub)
        
        logger.info(
            f"Processed expired subscription #{sub.subscription_id} "
            f"for user {sub.telegram_id}"
        )
    
    async def _handle_expiring(self, sub: ExpiringSubscription) -> None:
        """Обработка скоро истекающей подписки."""
        # Вызываем callback для уведомления
        if self._on_expiring:
            await self._on_expiring(sub)
        
        logger.debug(
            f"Expiring subscription #{sub.subscription_id}: "
            f"{sub.days_left} days left"
        )
    
    async def _count_active_subscriptions(self) -> int:
        """Подсчёт активных подписок."""
        from database.crud import UserSubscriptionCRUD
        from database.models import SubscriptionStatus
        
        with self.get_session() as session:
            return UserSubscriptionCRUD.count_by_status(
                session, SubscriptionStatus.ACTIVE
            )


# ═══════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ CRUD
# ═══════════════════════════════════════════════════════════════════════════

def extend_user_subscription_crud():
    """
    Расширение UserSubscriptionCRUD дополнительными методами.
    
    Эти методы нужно добавить в database/crud.py
    """
    
    code = '''
    @classmethod
    def get_expired_active(
        cls,
        session: Session,
        before_date: datetime,
    ) -> List["UserSubscription"]:
        """Получение активных подписок с истекшим сроком."""
        return session.query(UserSubscription).filter(
            UserSubscription.status == SubscriptionStatus.ACTIVE,
            UserSubscription.end_date < before_date,
            UserSubscription.end_date.isnot(None),
        ).all()
    
    @classmethod
    def get_expiring_between(
        cls,
        session: Session,
        start_date: datetime,
        end_date: datetime,
    ) -> List["UserSubscription"]:
        """Получение подписок, истекающих в указанный период."""
        return session.query(UserSubscription).filter(
            UserSubscription.status == SubscriptionStatus.ACTIVE,
            UserSubscription.end_date >= start_date,
            UserSubscription.end_date <= end_date,
        ).all()
    
    @classmethod
    def count_by_status(
        cls,
        session: Session,
        status: SubscriptionStatus,
    ) -> int:
        """Подсчёт подписок по статусу."""
        return session.query(UserSubscription).filter(
            UserSubscription.status == status
        ).count()
    
    @classmethod
    def update_status(
        cls,
        session: Session,
        subscription_id: int,
        status: SubscriptionStatus,
    ) -> bool:
        """Обновление статуса подписки."""
        result = session.query(UserSubscription).filter(
            UserSubscription.id == subscription_id
        ).update({"status": status})
        session.commit()
        return result > 0
    '''
    
    return code


# ═══════════════════════════════════════════════════════════════════════════
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ═══════════════════════════════════════════════════════════════════════════

async def setup_subscription_checker(
    bot: Bot,
    get_session: Callable,
    check_interval: int = 3600,
) -> SubscriptionChecker:
    """
    Настройка и запуск чекера подписок.
    
    Args:
        bot: Экземпляр бота
        get_session: Функция получения сессии БД
        check_interval: Интервал проверки
        
    Returns:
        Настроенный чекер
    """
    from services.channel_manager import ChannelManager
    
    channel_manager = ChannelManager(bot)
    
    checker = SubscriptionChecker(
        bot=bot,
        get_session=get_session,
        channel_manager=channel_manager,
        check_interval=check_interval,
        warning_days=[7, 3, 1],
        auto_kick=True,
        grace_period_hours=0,
    )
    
    # Callback для истекших подписок
    async def on_expired(sub: ExpiredSubscription):
        try:
            from utils.i18n import t
            
            # Отправляем уведомление пользователю
            text = t(
                "subscription_expired",
                "ru",  # Нужно получать язык пользователя
                item_name=sub.item_name,
            )
            
            await bot.send_message(
                chat_id=sub.telegram_id,
                text=text,
            )
        except TelegramAPIError as e:
            logger.error(f"Error sending expiration notification: {e}")
    
    # Callback для скоро истекающих
    async def on_expiring(sub: ExpiringSubscription):
        try:
            from utils.i18n import t
            
            text = t(
                "subscription_expiring_soon",
                "ru",
                item_name=sub.item_name,
                days=sub.days_left,
            )
            
            await bot.send_message(
                chat_id=sub.telegram_id,
                text=text,
            )
        except TelegramAPIError as e:
            logger.error(f"Error sending expiring notification: {e}")
    
    checker.on_expired(on_expired)
    checker.on_expiring(on_expiring)
    
    return checker
