"""
═══════════════════════════════════════════════════════════════════════════════
📁 database/crud.py — CRUD операции
═══════════════════════════════════════════════════════════════════════════════
Все операции создания, чтения, обновления и удаления для моделей.
═══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Any
import secrets
import string

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from database.models import (
    User, Channel, SubscriptionPlan, SubscriptionPackage, PackageChannel,
    PackagePlan, UserSubscription, Payment, Promocode, PromocodeUsage,
    MenuButton, BotText, DailyStats, ActivityLog, Broadcast, BotSettings,
    Language, SubscriptionType, SubscriptionStatus, PaymentStatus,
    PromocodeType, MenuButtonType
)


# ═══════════════════════════════════════════════════════════════════════════════
# 👤 ПОЛЬЗОВАТЕЛИ (USERS)
# ═══════════════════════════════════════════════════════════════════════════════

class UserCRUD:
    """CRUD операции для пользователей."""
    
    @staticmethod
    def get_by_telegram_id(session: Session, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID."""
        return session.query(User).filter(User.telegram_id == telegram_id).first()
    
    @staticmethod
    def get_by_id(session: Session, user_id: int) -> Optional[User]:
        """Получить пользователя по ID."""
        return session.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create(
        session: Session,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language: Language = Language.RU,
        referred_by: Optional[int] = None
    ) -> User:
        """Создать нового пользователя."""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
            referred_by=referred_by,
            referral_code=UserCRUD._generate_referral_code()
        )
        session.add(user)
        session.flush()
        return user
    
    @staticmethod
    def get_or_create(
        session: Session,
        telegram_id: int,
        **kwargs
    ) -> Tuple[User, bool]:
        """
        Получить или создать пользователя.
        
        Returns:
            Tuple[User, bool]: (пользователь, создан_новый)
        """
        user = UserCRUD.get_by_telegram_id(session, telegram_id)
        if user:
            # Обновляем данные
            if kwargs.get("username"):
                user.username = kwargs["username"]
            if kwargs.get("first_name"):
                user.first_name = kwargs["first_name"]
            if kwargs.get("last_name"):
                user.last_name = kwargs["last_name"]
            user.last_activity = datetime.utcnow()
            return user, False
        
        user = UserCRUD.create(session, telegram_id, **kwargs)
        return user, True
    
    @staticmethod
    def update_language(session: Session, user_id: int, language: Language) -> Optional[User]:
        """Обновить язык пользователя."""
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.language = language
        return user
    
    @staticmethod
    def update_activity(session: Session, user_id: int) -> None:
        """Обновить время последней активности."""
        session.query(User).filter(User.id == user_id).update(
            {"last_activity": datetime.utcnow()}
        )
    
    @staticmethod
    def block_user(session: Session, user_id: int, block: bool = True) -> Optional[User]:
        """Заблокировать/разблокировать пользователя."""
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.is_blocked = block
        return user
    
    @staticmethod
    def set_admin(session: Session, user_id: int, is_admin: bool = True) -> Optional[User]:
        """Установить/снять права администратора."""
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.is_admin = is_admin
        return user
    
    @staticmethod
    def add_spent(session: Session, user_id: int, amount: float) -> None:
        """Добавить сумму к общим тратам пользователя."""
        session.query(User).filter(User.id == user_id).update(
            {"total_spent": User.total_spent + amount}
        )
    
    @staticmethod
    def get_all(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        is_blocked: Optional[bool] = None,
        language: Optional[Language] = None
    ) -> List[User]:
        """Получить список пользователей с фильтрами."""
        query = session.query(User)
        
        if is_blocked is not None:
            query = query.filter(User.is_blocked == is_blocked)
        if language:
            query = query.filter(User.language == language)
        
        return query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def count(session: Session, is_blocked: Optional[bool] = None) -> int:
        """Подсчитать количество пользователей."""
        query = session.query(func.count(User.id))
        if is_blocked is not None:
            query = query.filter(User.is_blocked == is_blocked)
        return query.scalar() or 0
    
    @staticmethod
    def get_by_referral_code(session: Session, code: str) -> Optional[User]:
        """Получить пользователя по реферальному коду."""
        return session.query(User).filter(User.referral_code == code).first()
    
    @staticmethod
    def _generate_referral_code(length: int = 8) -> str:
        """Генерация уникального реферального кода."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 КАНАЛЫ (CHANNELS)
# ═══════════════════════════════════════════════════════════════════════════════

class ChannelCRUD:
    """CRUD операции для каналов."""
    
    @staticmethod
    def get_by_id(session: Session, channel_id: int) -> Optional[Channel]:
        """Получить канал по ID."""
        return session.query(Channel).filter(Channel.id == channel_id).first()
    
    @staticmethod
    def get_by_telegram_id(session: Session, telegram_id: int) -> Optional[Channel]:
        """Получить канал по Telegram ID."""
        return session.query(Channel).filter(Channel.telegram_id == telegram_id).first()
    
    @staticmethod
    def create(
        session: Session,
        telegram_id: int,
        name_ru: str,
        name_en: Optional[str] = None,
        description_ru: Optional[str] = None,
        description_en: Optional[str] = None,
        username: Optional[str] = None,
        image_url: Optional[str] = None,
        preview_link: Optional[str] = None,
        trial_enabled: bool = False,
        trial_days: int = 1
    ) -> Channel:
        """Создать новый канал."""
        channel = Channel(
            telegram_id=telegram_id,
            name_ru=name_ru,
            name_en=name_en,
            description_ru=description_ru,
            description_en=description_en,
            username=username,
            image_url=image_url,
            preview_link=preview_link,
            trial_enabled=trial_enabled,
            trial_days=trial_days
        )
        session.add(channel)
        session.flush()
        return channel
    
    @staticmethod
    def update(
        session: Session,
        channel_id: int,
        **kwargs
    ) -> Optional[Channel]:
        """Обновить канал."""
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            for key, value in kwargs.items():
                if hasattr(channel, key):
                    setattr(channel, key, value)
        return channel
    
    @staticmethod
    def delete(session: Session, channel_id: int) -> bool:
        """Удалить канал."""
        result = session.query(Channel).filter(Channel.id == channel_id).delete()
        return result > 0
    
    @staticmethod
    def get_active(session: Session) -> List[Channel]:
        """Получить список активных каналов."""
        return session.query(Channel).filter(
            Channel.is_active == True
        ).order_by(Channel.sort_order, Channel.id).all()
    
    @staticmethod
    def get_all(session: Session, include_inactive: bool = False) -> List[Channel]:
        """Получить все каналы."""
        query = session.query(Channel)
        if not include_inactive:
            query = query.filter(Channel.is_active == True)
        return query.order_by(Channel.sort_order, Channel.id).all()
    
    @staticmethod
    def set_active(session: Session, channel_id: int, is_active: bool) -> Optional[Channel]:
        """Активировать/деактивировать канал."""
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if channel:
            channel.is_active = is_active
        return channel


# ═══════════════════════════════════════════════════════════════════════════════
# 💰 ТАРИФНЫЕ ПЛАНЫ (SUBSCRIPTION PLANS)
# ═══════════════════════════════════════════════════════════════════════════════

class SubscriptionPlanCRUD:
    """CRUD операции для тарифных планов каналов."""
    
    @staticmethod
    def get_by_id(session: Session, plan_id: int) -> Optional[SubscriptionPlan]:
        """Получить план по ID."""
        return session.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    
    @staticmethod
    def create(
        session: Session,
        channel_id: int,
        name_ru: str,
        duration_days: int,
        price: float,
        name_en: Optional[str] = None,
        old_price: Optional[float] = None
    ) -> SubscriptionPlan:
        """Создать новый тарифный план."""
        plan = SubscriptionPlan(
            channel_id=channel_id,
            name_ru=name_ru,
            name_en=name_en,
            duration_days=duration_days,
            price=price,
            old_price=old_price
        )
        session.add(plan)
        session.flush()
        return plan
    
    @staticmethod
    def update(session: Session, plan_id: int, **kwargs) -> Optional[SubscriptionPlan]:
        """Обновить тарифный план."""
        plan = session.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if plan:
            for key, value in kwargs.items():
                if hasattr(plan, key):
                    setattr(plan, key, value)
        return plan
    
    @staticmethod
    def delete(session: Session, plan_id: int) -> bool:
        """Удалить тарифный план."""
        result = session.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).delete()
        return result > 0
    
    @staticmethod
    def get_by_channel(session: Session, channel_id: int, active_only: bool = True) -> List[SubscriptionPlan]:
        """Получить планы для канала."""
        query = session.query(SubscriptionPlan).filter(SubscriptionPlan.channel_id == channel_id)
        if active_only:
            query = query.filter(SubscriptionPlan.is_active == True)
        return query.order_by(SubscriptionPlan.sort_order, SubscriptionPlan.duration_days).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ПАКЕТЫ ПОДПИСОК (SUBSCRIPTION PACKAGES)
# ═══════════════════════════════════════════════════════════════════════════════

class PackageCRUD:
    """CRUD операции для пакетов подписок."""
    
    @staticmethod
    def get_by_id(session: Session, package_id: int) -> Optional[SubscriptionPackage]:
        """Получить пакет по ID."""
        return session.query(SubscriptionPackage).filter(SubscriptionPackage.id == package_id).first()
    
    @staticmethod
    def create(
        session: Session,
        name_ru: str,
        name_en: Optional[str] = None,
        description_ru: Optional[str] = None,
        description_en: Optional[str] = None,
        image_url: Optional[str] = None,
        trial_enabled: bool = False,
        trial_days: int = 1
    ) -> SubscriptionPackage:
        """Создать новый пакет."""
        package = SubscriptionPackage(
            name_ru=name_ru,
            name_en=name_en,
            description_ru=description_ru,
            description_en=description_en,
            image_url=image_url,
            trial_enabled=trial_enabled,
            trial_days=trial_days
        )
        session.add(package)
        session.flush()
        return package
    
    @staticmethod
    def update(session: Session, package_id: int, **kwargs) -> Optional[SubscriptionPackage]:
        """Обновить пакет."""
        package = session.query(SubscriptionPackage).filter(SubscriptionPackage.id == package_id).first()
        if package:
            for key, value in kwargs.items():
                if hasattr(package, key):
                    setattr(package, key, value)
        return package
    
    @staticmethod
    def delete(session: Session, package_id: int) -> bool:
        """Удалить пакет."""
        result = session.query(SubscriptionPackage).filter(SubscriptionPackage.id == package_id).delete()
        return result > 0
    
    @staticmethod
    def get_active(session: Session) -> List[SubscriptionPackage]:
        """Получить активные пакеты."""
        return session.query(SubscriptionPackage).filter(
            SubscriptionPackage.is_active == True
        ).order_by(SubscriptionPackage.sort_order, SubscriptionPackage.id).all()
    
    @staticmethod
    def get_all(session: Session, include_inactive: bool = False) -> List[SubscriptionPackage]:
        """Получить все пакеты."""
        query = session.query(SubscriptionPackage)
        if not include_inactive:
            query = query.filter(SubscriptionPackage.is_active == True)
        return query.order_by(SubscriptionPackage.sort_order, SubscriptionPackage.id).all()
    
    @staticmethod
    def add_channel(session: Session, package_id: int, channel_id: int) -> PackageChannel:
        """Добавить канал в пакет."""
        # Проверяем, нет ли уже такой связи
        existing = session.query(PackageChannel).filter(
            PackageChannel.package_id == package_id,
            PackageChannel.channel_id == channel_id
        ).first()
        
        if existing:
            return existing
        
        pc = PackageChannel(package_id=package_id, channel_id=channel_id)
        session.add(pc)
        session.flush()
        return pc
    
    @staticmethod
    def remove_channel(session: Session, package_id: int, channel_id: int) -> bool:
        """Удалить канал из пакета."""
        result = session.query(PackageChannel).filter(
            PackageChannel.package_id == package_id,
            PackageChannel.channel_id == channel_id
        ).delete()
        return result > 0
    
    @staticmethod
    def get_channels(session: Session, package_id: int) -> List[Channel]:
        """Получить каналы пакета."""
        return session.query(Channel).join(PackageChannel).filter(
            PackageChannel.package_id == package_id
        ).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 💰 ТАРИФНЫЕ ПЛАНЫ ПАКЕТОВ (PACKAGE PLANS)
# ═══════════════════════════════════════════════════════════════════════════════

class PackagePlanCRUD:
    """CRUD операции для тарифных планов пакетов."""
    
    @staticmethod
    def get_by_id(session: Session, plan_id: int) -> Optional[PackagePlan]:
        """Получить план по ID."""
        return session.query(PackagePlan).filter(PackagePlan.id == plan_id).first()
    
    @staticmethod
    def create(
        session: Session,
        package_id: int,
        name_ru: str,
        duration_days: int,
        price: float,
        name_en: Optional[str] = None,
        old_price: Optional[float] = None
    ) -> PackagePlan:
        """Создать новый план для пакета."""
        plan = PackagePlan(
            package_id=package_id,
            name_ru=name_ru,
            name_en=name_en,
            duration_days=duration_days,
            price=price,
            old_price=old_price
        )
        session.add(plan)
        session.flush()
        return plan
    
    @staticmethod
    def get_by_package(session: Session, package_id: int, active_only: bool = True) -> List[PackagePlan]:
        """Получить планы для пакета."""
        query = session.query(PackagePlan).filter(PackagePlan.package_id == package_id)
        if active_only:
            query = query.filter(PackagePlan.is_active == True)
        return query.order_by(PackagePlan.sort_order, PackagePlan.duration_days).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ПОДПИСКИ ПОЛЬЗОВАТЕЛЕЙ (USER SUBSCRIPTIONS)
# ═══════════════════════════════════════════════════════════════════════════════

class UserSubscriptionCRUD:
    """CRUD операции для подписок пользователей."""
    
    @staticmethod
    def get_by_id(session: Session, subscription_id: int) -> Optional[UserSubscription]:
        """Получить подписку по ID."""
        return session.query(UserSubscription).filter(UserSubscription.id == subscription_id).first()
    
    @staticmethod
    def create_channel_subscription(
        session: Session,
        user_id: int,
        channel_id: int,
        duration_days: int,
        payment_id: Optional[int] = None,
        is_trial: bool = False
    ) -> UserSubscription:
        """Создать подписку на канал."""
        expires_at = None
        if duration_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        status = SubscriptionStatus.TRIAL if is_trial else SubscriptionStatus.ACTIVE
        
        subscription = UserSubscription(
            user_id=user_id,
            subscription_type=SubscriptionType.CHANNEL,
            channel_id=channel_id,
            status=status,
            expires_at=expires_at,
            payment_id=payment_id,
            is_trial=is_trial
        )
        session.add(subscription)
        session.flush()
        return subscription
    
    @staticmethod
    def create_package_subscription(
        session: Session,
        user_id: int,
        package_id: int,
        duration_days: int,
        payment_id: Optional[int] = None,
        is_trial: bool = False
    ) -> UserSubscription:
        """Создать подписку на пакет."""
        expires_at = None
        if duration_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        status = SubscriptionStatus.TRIAL if is_trial else SubscriptionStatus.ACTIVE
        
        subscription = UserSubscription(
            user_id=user_id,
            subscription_type=SubscriptionType.PACKAGE,
            package_id=package_id,
            status=status,
            expires_at=expires_at,
            payment_id=payment_id,
            is_trial=is_trial
        )
        session.add(subscription)
        session.flush()
        return subscription
    
    @staticmethod
    def get_user_subscriptions(
        session: Session,
        user_id: int,
        active_only: bool = True
    ) -> List[UserSubscription]:
        """Получить подписки пользователя."""
        query = session.query(UserSubscription).filter(UserSubscription.user_id == user_id)
        if active_only:
            query = query.filter(
                UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
            )
        return query.all()
    
    @staticmethod
    def get_user_channel_subscription(
        session: Session,
        user_id: int,
        channel_id: int
    ) -> Optional[UserSubscription]:
        """Получить активную подписку пользователя на канал."""
        return session.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.channel_id == channel_id,
            UserSubscription.subscription_type == SubscriptionType.CHANNEL,
            UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
        ).first()
    
    @staticmethod
    def get_user_package_subscription(
        session: Session,
        user_id: int,
        package_id: int
    ) -> Optional[UserSubscription]:
        """Получить активную подписку пользователя на пакет."""
        return session.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.package_id == package_id,
            UserSubscription.subscription_type == SubscriptionType.PACKAGE,
            UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
        ).first()
    
    @staticmethod
    def has_access_to_channel(session: Session, user_id: int, channel_id: int) -> bool:
        """Проверить, есть ли у пользователя доступ к каналу."""
        # Прямая подписка на канал
        direct = session.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.channel_id == channel_id,
            UserSubscription.subscription_type == SubscriptionType.CHANNEL,
            UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            or_(
                UserSubscription.expires_at.is_(None),
                UserSubscription.expires_at > datetime.utcnow()
            )
        ).first()
        
        if direct:
            return True
        
        # Подписка через пакет
        package_sub = session.query(UserSubscription).join(
            SubscriptionPackage
        ).join(
            PackageChannel
        ).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.subscription_type == SubscriptionType.PACKAGE,
            UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            or_(
                UserSubscription.expires_at.is_(None),
                UserSubscription.expires_at > datetime.utcnow()
            ),
            PackageChannel.channel_id == channel_id
        ).first()
        
        return package_sub is not None
    
    @staticmethod
    def get_expiring_soon(session: Session, days: int = 3) -> List[UserSubscription]:
        """Получить подписки, истекающие в ближайшие N дней."""
        deadline = datetime.utcnow() + timedelta(days=days)
        return session.query(UserSubscription).filter(
            UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            UserSubscription.expires_at.isnot(None),
            UserSubscription.expires_at <= deadline,
            UserSubscription.expires_at > datetime.utcnow(),
            UserSubscription.expiry_notified == False
        ).all()
    
    @staticmethod
    def get_expired(session: Session) -> List[UserSubscription]:
        """Получить истекшие подписки (для автокика)."""
        return session.query(UserSubscription).filter(
            UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            UserSubscription.expires_at.isnot(None),
            UserSubscription.expires_at <= datetime.utcnow()
        ).all()
    
    @staticmethod
    def mark_expired(session: Session, subscription_id: int) -> None:
        """Пометить подписку как истекшую."""
        session.query(UserSubscription).filter(
            UserSubscription.id == subscription_id
        ).update({"status": SubscriptionStatus.EXPIRED})
    
    @staticmethod
    def mark_notified(session: Session, subscription_id: int) -> None:
        """Пометить, что уведомление об истечении отправлено."""
        session.query(UserSubscription).filter(
            UserSubscription.id == subscription_id
        ).update({"expiry_notified": True})
    
    @staticmethod
    def extend_subscription(
        session: Session,
        subscription_id: int,
        days: int
    ) -> Optional[UserSubscription]:
        """Продлить подписку на N дней."""
        sub = session.query(UserSubscription).filter(UserSubscription.id == subscription_id).first()
        if sub:
            if sub.expires_at is None:
                return sub  # Уже пожизненная
            
            # Если истекла, продлеваем от текущего момента
            base_date = max(sub.expires_at, datetime.utcnow())
            sub.expires_at = base_date + timedelta(days=days)
            sub.status = SubscriptionStatus.ACTIVE
            sub.expiry_notified = False
        return sub
    
    @staticmethod
    def has_used_trial(session: Session, user_id: int, channel_id: int = None, package_id: int = None) -> bool:
        """Проверить, использовал ли пользователь пробный период."""
        query = session.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.is_trial == True
        )
        if channel_id:
            query = query.filter(UserSubscription.channel_id == channel_id)
        if package_id:
            query = query.filter(UserSubscription.package_id == package_id)
        return query.first() is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 💳 ПЛАТЕЖИ (PAYMENTS)
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentCRUD:
    """CRUD операции для платежей."""
    
    @staticmethod
    def get_by_id(session: Session, payment_id: int) -> Optional[Payment]:
        """Получить платёж по ID."""
        return session.query(Payment).filter(Payment.id == payment_id).first()
    
    @staticmethod
    def get_by_invoice_id(session: Session, invoice_id: int) -> Optional[Payment]:
        """Получить платёж по ID инвойса Crypto Bot."""
        return session.query(Payment).filter(Payment.invoice_id == invoice_id).first()
    
    @staticmethod
    def create(
        session: Session,
        user_id: int,
        invoice_id: int,
        amount: float,
        subscription_type: SubscriptionType,
        duration_days: int,
        channel_id: Optional[int] = None,
        package_id: Optional[int] = None,
        plan_id: Optional[int] = None,
        original_amount: Optional[float] = None,
        promocode_id: Optional[int] = None,
        discount_amount: float = 0.0,
        pay_url: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Payment:
        """Создать новый платёж."""
        payment = Payment(
            user_id=user_id,
            invoice_id=invoice_id,
            amount=amount,
            original_amount=original_amount or amount,
            subscription_type=subscription_type,
            channel_id=channel_id,
            package_id=package_id,
            plan_id=plan_id,
            duration_days=duration_days,
            promocode_id=promocode_id,
            discount_amount=discount_amount,
            pay_url=pay_url,
            expires_at=expires_at
        )
        session.add(payment)
        session.flush()
        return payment
    
    @staticmethod
    def mark_paid(
        session: Session,
        payment_id: int,
        crypto_currency: Optional[str] = None
    ) -> Optional[Payment]:
        """Отметить платёж как оплаченный."""
        payment = session.query(Payment).filter(Payment.id == payment_id).first()
        if payment:
            payment.status = PaymentStatus.PAID
            payment.paid_at = datetime.utcnow()
            if crypto_currency:
                payment.crypto_currency = crypto_currency
        return payment
    
    @staticmethod
    def mark_expired(session: Session, payment_id: int) -> None:
        """Отметить платёж как просроченный."""
        session.query(Payment).filter(Payment.id == payment_id).update(
            {"status": PaymentStatus.EXPIRED}
        )
    
    @staticmethod
    def get_user_payments(
        session: Session,
        user_id: int,
        limit: int = 50
    ) -> List[Payment]:
        """Получить платежи пользователя."""
        return session.query(Payment).filter(
            Payment.user_id == user_id
        ).order_by(desc(Payment.created_at)).limit(limit).all()
    
    @staticmethod
    def get_pending(session: Session) -> List[Payment]:
        """Получить ожидающие платежи."""
        return session.query(Payment).filter(
            Payment.status == PaymentStatus.PENDING
        ).all()
    
    @staticmethod
    def get_stats(
        session: Session,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> dict:
        """Получить статистику платежей."""
        query = session.query(Payment).filter(Payment.status == PaymentStatus.PAID)
        
        if start_date:
            query = query.filter(Payment.paid_at >= start_date)
        if end_date:
            query = query.filter(Payment.paid_at <= end_date)
        
        payments = query.all()
        
        return {
            "count": len(payments),
            "total_amount": sum(p.amount for p in payments),
            "total_discounts": sum(p.discount_amount for p in payments)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ПРОМОКОДЫ (PROMOCODES)
# ═══════════════════════════════════════════════════════════════════════════════

class PromocodeCRUD:
    """CRUD операции для промокодов."""
    
    @staticmethod
    def get_by_id(session: Session, promocode_id: int) -> Optional[Promocode]:
        """Получить промокод по ID."""
        return session.query(Promocode).filter(Promocode.id == promocode_id).first()
    
    @staticmethod
    def get_by_code(session: Session, code: str) -> Optional[Promocode]:
        """Получить промокод по коду."""
        return session.query(Promocode).filter(
            func.upper(Promocode.code) == code.upper()
        ).first()
    
    @staticmethod
    def create(
        session: Session,
        code: str,
        promo_type: PromocodeType,
        value: float,
        max_uses: Optional[int] = None,
        channel_id: Optional[int] = None,
        package_id: Optional[int] = None,
        valid_until: Optional[datetime] = None,
        one_per_user: bool = True,
        min_plan_price: Optional[float] = None
    ) -> Promocode:
        """Создать новый промокод."""
        promocode = Promocode(
            code=code.upper(),
            type=promo_type,
            value=value,
            max_uses=max_uses,
            channel_id=channel_id,
            package_id=package_id,
            valid_until=valid_until,
            one_per_user=one_per_user,
            min_plan_price=min_plan_price
        )
        session.add(promocode)
        session.flush()
        return promocode
    
    @staticmethod
    def validate(
        session: Session,
        code: str,
        user_id: int,
        channel_id: Optional[int] = None,
        package_id: Optional[int] = None,
        plan_price: Optional[float] = None
    ) -> Tuple[bool, Optional[Promocode], str]:
        """
        Валидация промокода.
        
        Returns:
            Tuple[bool, Optional[Promocode], str]: (валиден, промокод, сообщение об ошибке)
        """
        promo = PromocodeCRUD.get_by_code(session, code)
        
        if not promo:
            return False, None, "promocode_not_found"
        
        if not promo.is_valid:
            if not promo.is_active:
                return False, None, "promocode_inactive"
            if promo.max_uses and promo.current_uses >= promo.max_uses:
                return False, None, "promocode_max_uses"
            if promo.valid_until and datetime.utcnow() > promo.valid_until:
                return False, None, "promocode_expired"
            return False, None, "promocode_invalid"
        
        # Проверка привязки к каналу/пакету
        if promo.channel_id and channel_id and promo.channel_id != channel_id:
            return False, None, "promocode_wrong_channel"
        if promo.package_id and package_id and promo.package_id != package_id:
            return False, None, "promocode_wrong_package"
        
        # Проверка минимальной цены
        if promo.min_plan_price and plan_price and plan_price < promo.min_plan_price:
            return False, None, "promocode_min_price"
        
        # Проверка использования пользователем
        if promo.one_per_user:
            used = session.query(PromocodeUsage).filter(
                PromocodeUsage.promocode_id == promo.id,
                PromocodeUsage.user_id == user_id
            ).first()
            if used:
                return False, None, "promocode_already_used"
        
        return True, promo, ""
    
    @staticmethod
    def use(
        session: Session,
        promocode_id: int,
        user_id: int,
        payment_id: Optional[int] = None,
        discount_amount: float = 0
    ) -> PromocodeUsage:
        """Использовать промокод."""
        # Увеличиваем счётчик использований
        session.query(Promocode).filter(Promocode.id == promocode_id).update(
            {"current_uses": Promocode.current_uses + 1}
        )
        
        # Создаём запись об использовании
        usage = PromocodeUsage(
            promocode_id=promocode_id,
            user_id=user_id,
            payment_id=payment_id,
            discount_amount=discount_amount
        )
        session.add(usage)
        session.flush()
        return usage
    
    @staticmethod
    def get_all(session: Session, active_only: bool = True) -> List[Promocode]:
        """Получить все промокоды."""
        query = session.query(Promocode)
        if active_only:
            query = query.filter(Promocode.is_active == True)
        return query.order_by(desc(Promocode.created_at)).all()
    
    @staticmethod
    def deactivate(session: Session, promocode_id: int) -> Optional[Promocode]:
        """Деактивировать промокод."""
        promo = session.query(Promocode).filter(Promocode.id == promocode_id).first()
        if promo:
            promo.is_active = False
        return promo
    
    @staticmethod
    def generate_code(length: int = 8) -> str:
        """Генерация случайного кода."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))


# ═══════════════════════════════════════════════════════════════════════════════
# 🏗️ КОНСТРУКТОР МЕНЮ (MENU BUTTONS)
# ═══════════════════════════════════════════════════════════════════════════════

class MenuButtonCRUD:
    """CRUD операции для кнопок меню."""
    
    @staticmethod
    def get_by_id(session: Session, button_id: int) -> Optional[MenuButton]:
        """Получить кнопку по ID."""
        return session.query(MenuButton).filter(MenuButton.id == button_id).first()
    
    @staticmethod
    def get_by_key(session: Session, button_key: str) -> Optional[MenuButton]:
        """Получить кнопку по ключу."""
        return session.query(MenuButton).filter(MenuButton.button_key == button_key).first()
    
    @staticmethod
    def create(
        session: Session,
        button_key: str,
        button_type: MenuButtonType,
        text_ru: str,
        text_en: Optional[str] = None,
        url: Optional[str] = None,
        content_ru: Optional[str] = None,
        content_en: Optional[str] = None,
        image_url: Optional[str] = None,
        parent_id: Optional[int] = None,
        is_system: bool = False,
        row: int = 0
    ) -> MenuButton:
        """Создать новую кнопку."""
        # Получаем максимальный sort_order для родителя
        max_order = session.query(func.max(MenuButton.sort_order)).filter(
            MenuButton.parent_id == parent_id
        ).scalar() or 0
        
        button = MenuButton(
            button_key=button_key,
            button_type=button_type,
            text_ru=text_ru,
            text_en=text_en,
            url=url,
            content_ru=content_ru,
            content_en=content_en,
            image_url=image_url,
            parent_id=parent_id,
            is_system=is_system,
            sort_order=max_order + 1,
            row=row
        )
        session.add(button)
        session.flush()
        return button
    
    @staticmethod
    def update(session: Session, button_id: int, **kwargs) -> Optional[MenuButton]:
        """Обновить кнопку."""
        button = session.query(MenuButton).filter(MenuButton.id == button_id).first()
        if button:
            # Системные кнопки нельзя менять тип
            if button.is_system and "button_type" in kwargs:
                del kwargs["button_type"]
            
            for key, value in kwargs.items():
                if hasattr(button, key):
                    setattr(button, key, value)
        return button
    
    @staticmethod
    def delete(session: Session, button_id: int) -> bool:
        """Удалить кнопку (только не системные)."""
        button = session.query(MenuButton).filter(MenuButton.id == button_id).first()
        if button and not button.is_system:
            session.delete(button)
            return True
        return False
    
    @staticmethod
    def get_main_menu(session: Session) -> List[MenuButton]:
        """Получить кнопки главного меню."""
        return session.query(MenuButton).filter(
            MenuButton.parent_id.is_(None),
            MenuButton.is_active == True
        ).order_by(MenuButton.row, MenuButton.sort_order).all()
    
    @staticmethod
    def get_children(session: Session, parent_id: int) -> List[MenuButton]:
        """Получить дочерние кнопки."""
        return session.query(MenuButton).filter(
            MenuButton.parent_id == parent_id,
            MenuButton.is_active == True
        ).order_by(MenuButton.row, MenuButton.sort_order).all()
    
    @staticmethod
    def reorder(session: Session, button_id: int, new_order: int) -> None:
        """Изменить порядок кнопки."""
        session.query(MenuButton).filter(MenuButton.id == button_id).update(
            {"sort_order": new_order}
        )
    
    @staticmethod
    def init_default_buttons(session: Session) -> None:
        """Инициализация системных кнопок по умолчанию."""
        defaults = [
            {
                "button_key": "catalog",
                "button_type": MenuButtonType.CATALOG,
                "text_ru": "📢 Каталог",
                "text_en": "📢 Catalog",
                "is_system": True,
                "row": 0
            },
            {
                "button_key": "profile",
                "button_type": MenuButtonType.PROFILE,
                "text_ru": "👤 Профиль",
                "text_en": "👤 Profile",
                "is_system": True,
                "row": 1
            },
            {
                "button_key": "promocode",
                "button_type": MenuButtonType.PROMOCODE,
                "text_ru": "🎟️ Промокод",
                "text_en": "🎟️ Promocode",
                "is_system": True,
                "row": 1
            },
            {
                "button_key": "support",
                "button_type": MenuButtonType.SUPPORT,
                "text_ru": "💬 Поддержка",
                "text_en": "💬 Support",
                "is_system": True,
                "row": 2
            },
            {
                "button_key": "language",
                "button_type": MenuButtonType.LANGUAGE,
                "text_ru": "🌐 Язык",
                "text_en": "🌐 Language",
                "is_system": True,
                "row": 2
            }
        ]
        
        for btn_data in defaults:
            existing = MenuButtonCRUD.get_by_key(session, btn_data["button_key"])
            if not existing:
                MenuButtonCRUD.create(session, **btn_data)


# ═══════════════════════════════════════════════════════════════════════════════
# 📝 ТЕКСТЫ БОТА (BOT TEXTS)
# ═══════════════════════════════════════════════════════════════════════════════

class BotTextCRUD:
    """CRUD операции для текстов бота."""
    
    @staticmethod
    def get_by_key(session: Session, text_key: str) -> Optional[BotText]:
        """Получить текст по ключу."""
        return session.query(BotText).filter(BotText.text_key == text_key).first()
    
    @staticmethod
    def get_text(session: Session, text_key: str, lang: str = "ru", **kwargs) -> str:
        """Получить текст с подстановкой переменных."""
        bot_text = BotTextCRUD.get_by_key(session, text_key)
        if bot_text:
            return bot_text.get_text(lang, **kwargs)
        return f"[{text_key}]"  # Fallback если текст не найден
    
    @staticmethod
    def create(
        session: Session,
        text_key: str,
        text_ru: str,
        text_en: Optional[str] = None,
        description: Optional[str] = None,
        variables: Optional[List[str]] = None,
        is_system: bool = False
    ) -> BotText:
        """Создать новый текст."""
        bot_text = BotText(
            text_key=text_key,
            text_ru=text_ru,
            text_en=text_en,
            description=description,
            variables=variables,
            is_system=is_system
        )
        session.add(bot_text)
        session.flush()
        return bot_text
    
    @staticmethod
    def update(session: Session, text_key: str, **kwargs) -> Optional[BotText]:
        """Обновить текст."""
        bot_text = session.query(BotText).filter(BotText.text_key == text_key).first()
        if bot_text:
            for key, value in kwargs.items():
                if hasattr(bot_text, key) and key != "text_key":
                    setattr(bot_text, key, value)
        return bot_text
    
    @staticmethod
    def get_all(session: Session) -> List[BotText]:
        """Получить все тексты."""
        return session.query(BotText).order_by(BotText.text_key).all()
    
    @staticmethod
    def init_default_texts(session: Session) -> None:
        """Инициализация текстов по умолчанию."""
        defaults = [
            {
                "text_key": "welcome",
                "text_ru": "👋 Добро пожаловать, {user_name}!\n\nВыберите действие:",
                "text_en": "👋 Welcome, {user_name}!\n\nChoose an action:",
                "description": "Приветственное сообщение",
                "variables": ["user_name"],
                "is_system": True
            },
            {
                "text_key": "profile",
                "text_ru": "👤 <b>Ваш профиль</b>\n\n📱 ID: {user_id}\n👤 Имя: {user_name}\n📅 Регистрация: {reg_date}\n💰 Потрачено: ${spent}",
                "text_en": "👤 <b>Your profile</b>\n\n📱 ID: {user_id}\n👤 Name: {user_name}\n📅 Registered: {reg_date}\n💰 Spent: ${spent}",
                "description": "Профиль пользователя",
                "variables": ["user_id", "user_name", "reg_date", "spent"],
                "is_system": True
            },
            {
                "text_key": "catalog_title",
                "text_ru": "📢 <b>Каталог каналов</b>\n\nВыберите канал или пакет:",
                "text_en": "📢 <b>Channel Catalog</b>\n\nSelect a channel or package:",
                "description": "Заголовок каталога",
                "is_system": True
            },
            {
                "text_key": "channel_info",
                "text_ru": "📢 <b>{channel_name}</b>\n\n{description}\n\n💰 Цены:",
                "text_en": "📢 <b>{channel_name}</b>\n\n{description}\n\n💰 Prices:",
                "description": "Информация о канале",
                "variables": ["channel_name", "description"],
                "is_system": True
            },
            {
                "text_key": "package_info",
                "text_ru": "📦 <b>{package_name}</b>\n\n{description}\n\n📢 Каналы в пакете:\n{channels}\n\n💰 Цены:",
                "text_en": "📦 <b>{package_name}</b>\n\n{description}\n\n📢 Channels in package:\n{channels}\n\n💰 Prices:",
                "description": "Информация о пакете",
                "variables": ["package_name", "description", "channels"],
                "is_system": True
            },
            {
                "text_key": "payment_created",
                "text_ru": "💳 <b>Счёт на оплату</b>\n\n📦 {item_name}\n⏱️ Период: {duration}\n💰 Сумма: ${amount} USDT\n\nНажмите кнопку ниже для оплаты:",
                "text_en": "💳 <b>Payment Invoice</b>\n\n📦 {item_name}\n⏱️ Period: {duration}\n💰 Amount: ${amount} USDT\n\nClick the button below to pay:",
                "description": "Счёт создан",
                "variables": ["item_name", "duration", "amount"],
                "is_system": True
            },
            {
                "text_key": "payment_success",
                "text_ru": "✅ <b>Оплата успешна!</b>\n\n📦 {item_name}\n⏱️ Активно до: {expires_at}\n\n🔗 Ссылка для доступа:",
                "text_en": "✅ <b>Payment successful!</b>\n\n📦 {item_name}\n⏱️ Active until: {expires_at}\n\n🔗 Access link:",
                "description": "Оплата успешна",
                "variables": ["item_name", "expires_at"],
                "is_system": True
            },
            {
                "text_key": "subscription_expired",
                "text_ru": "⚠️ Ваша подписка на <b>{channel_name}</b> истекла.\n\nПродлите подписку, чтобы сохранить доступ!",
                "text_en": "⚠️ Your subscription to <b>{channel_name}</b> has expired.\n\nRenew your subscription to keep access!",
                "description": "Подписка истекла",
                "variables": ["channel_name"],
                "is_system": True
            },
            {
                "text_key": "subscription_expiring",
                "text_ru": "⏰ Ваша подписка на <b>{channel_name}</b> истекает через {days_left} дн.\n\nПродлите заранее, чтобы не потерять доступ!",
                "text_en": "⏰ Your subscription to <b>{channel_name}</b> expires in {days_left} days.\n\nRenew early to keep your access!",
                "description": "Подписка скоро истечёт",
                "variables": ["channel_name", "days_left"],
                "is_system": True
            },
            {
                "text_key": "promocode_enter",
                "text_ru": "🎟️ Введите промокод:",
                "text_en": "🎟️ Enter promocode:",
                "description": "Запрос промокода",
                "is_system": True
            },
            {
                "text_key": "promocode_success",
                "text_ru": "✅ Промокод применён! Скидка: {discount}",
                "text_en": "✅ Promocode applied! Discount: {discount}",
                "description": "Промокод применён",
                "variables": ["discount"],
                "is_system": True
            },
            {
                "text_key": "promocode_invalid",
                "text_ru": "❌ Неверный или недействительный промокод",
                "text_en": "❌ Invalid or expired promocode",
                "description": "Неверный промокод",
                "is_system": True
            },
            {
                "text_key": "trial_activated",
                "text_ru": "🎉 Пробный период активирован!\n\n📦 {item_name}\n⏱️ Действует до: {expires_at}",
                "text_en": "🎉 Trial period activated!\n\n📦 {item_name}\n⏱️ Valid until: {expires_at}",
                "description": "Пробный период активирован",
                "variables": ["item_name", "expires_at"],
                "is_system": True
            },
            {
                "text_key": "trial_used",
                "text_ru": "❌ Вы уже использовали пробный период",
                "text_en": "❌ You have already used the trial period",
                "description": "Пробный период уже использован",
                "is_system": True
            },
            {
                "text_key": "language_changed",
                "text_ru": "✅ Язык изменён на русский",
                "text_en": "✅ Language changed to English",
                "description": "Язык изменён",
                "is_system": True
            },
            {
                "text_key": "support_message",
                "text_ru": "💬 <b>Поддержка</b>\n\nЕсли у вас есть вопросы, напишите нам: @support",
                "text_en": "💬 <b>Support</b>\n\nIf you have questions, contact us: @support",
                "description": "Сообщение поддержки",
                "is_system": True
            },
            {
                "text_key": "no_subscriptions",
                "text_ru": "📭 У вас пока нет активных подписок",
                "text_en": "📭 You don't have any active subscriptions yet",
                "description": "Нет активных подписок",
                "is_system": True
            },
            {
                "text_key": "active_subscriptions",
                "text_ru": "📋 <b>Ваши активные подписки:</b>",
                "text_en": "📋 <b>Your active subscriptions:</b>",
                "description": "Заголовок списка подписок",
                "is_system": True
            }
        ]
        
        for txt_data in defaults:
            existing = BotTextCRUD.get_by_key(session, txt_data["text_key"])
            if not existing:
                BotTextCRUD.create(session, **txt_data)


# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ НАСТРОЙКИ БОТА (BOT SETTINGS)
# ═══════════════════════════════════════════════════════════════════════════════

class BotSettingsCRUD:
    """CRUD операции для настроек бота."""
    
    @staticmethod
    def get(session: Session, key: str, default: Any = None) -> Any:
        """Получить значение настройки."""
        setting = session.query(BotSettings).filter(BotSettings.key == key).first()
        if setting:
            return setting.typed_value
        return default
    
    @staticmethod
    def set(session: Session, key: str, value: Any, value_type: str = "string", description: str = None) -> BotSettings:
        """Установить значение настройки."""
        import json
        
        setting = session.query(BotSettings).filter(BotSettings.key == key).first()
        
        # Преобразуем значение в строку
        if value_type == "json":
            str_value = json.dumps(value)
        else:
            str_value = str(value)
        
        if setting:
            setting.value = str_value
            setting.value_type = value_type
            if description:
                setting.description = description
        else:
            setting = BotSettings(
                key=key,
                value=str_value,
                value_type=value_type,
                description=description
            )
            session.add(setting)
        
        session.flush()
        return setting
    
    @staticmethod
    def get_all(session: Session) -> dict:
        """Получить все настройки как словарь."""
        settings = session.query(BotSettings).all()
        return {s.key: s.typed_value for s in settings}


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 СТАТИСТИКА (DAILY STATS)
# ═══════════════════════════════════════════════════════════════════════════════

class StatsCRUD:
    """CRUD операции для статистики."""
    
    @staticmethod
    def update_daily_stats(session: Session) -> DailyStats:
        """Обновить/создать статистику за сегодня."""
        today = datetime.utcnow().date()
        today_dt = datetime.combine(today, datetime.min.time())
        
        stats = session.query(DailyStats).filter(
            func.date(DailyStats.date) == today
        ).first()
        
        if not stats:
            stats = DailyStats(date=today_dt)
            session.add(stats)
        
        # Подсчёт статистики
        stats.total_users = session.query(func.count(User.id)).scalar() or 0
        stats.new_users = session.query(func.count(User.id)).filter(
            func.date(User.created_at) == today
        ).scalar() or 0
        
        stats.active_subscriptions = session.query(func.count(UserSubscription.id)).filter(
            UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
        ).scalar() or 0
        
        stats.new_subscriptions = session.query(func.count(UserSubscription.id)).filter(
            func.date(UserSubscription.created_at) == today
        ).scalar() or 0
        
        # Платежи за сегодня
        paid_today = session.query(Payment).filter(
            Payment.status == PaymentStatus.PAID,
            func.date(Payment.paid_at) == today
        ).all()
        
        stats.payments_count = len(paid_today)
        stats.payments_amount = sum(p.amount for p in paid_today)
        
        session.flush()
        return stats
    
    @staticmethod
    def get_stats_range(session: Session, start_date: datetime, end_date: datetime) -> List[DailyStats]:
        """Получить статистику за период."""
        return session.query(DailyStats).filter(
            DailyStats.date >= start_date,
            DailyStats.date <= end_date
        ).order_by(DailyStats.date).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 📝 ЛОГИ АКТИВНОСТИ
# ═══════════════════════════════════════════════════════════════════════════════

class ActivityLogCRUD:
    """CRUD операции для логов активности."""
    
    @staticmethod
    def log(session: Session, action: str, user_id: int = None, details: dict = None) -> ActivityLog:
        """Записать лог активности."""
        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details
        )
        session.add(log)
        session.flush()
        return log
    
    @staticmethod
    def get_recent(session: Session, limit: int = 100, action: str = None) -> List[ActivityLog]:
        """Получить последние логи."""
        query = session.query(ActivityLog)
        if action:
            query = query.filter(ActivityLog.action == action)
        return query.order_by(desc(ActivityLog.created_at)).limit(limit).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 📨 РАССЫЛКА
# ═══════════════════════════════════════════════════════════════════════════════

class BroadcastCRUD:
    """CRUD операции для рассылок."""
    
    @staticmethod
    def create(
        session: Session,
        text_ru: str,
        text_en: Optional[str] = None,
        image_url: Optional[str] = None,
        buttons: Optional[list] = None,
        target_all: bool = True,
        target_lang: Optional[str] = None,
        target_has_subscription: Optional[bool] = None,
        target_channel_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Broadcast:
        """Создать новую рассылку."""
        broadcast = Broadcast(
            text_ru=text_ru,
            text_en=text_en,
            image_url=image_url,
            buttons=buttons,
            target_all=target_all,
            target_lang=target_lang,
            target_has_subscription=target_has_subscription,
            target_channel_id=target_channel_id,
            created_by=created_by
        )
        session.add(broadcast)
        session.flush()
        return broadcast
    
    @staticmethod
    def get_by_id(session: Session, broadcast_id: int) -> Optional[Broadcast]:
        """Получить рассылку по ID."""
        return session.query(Broadcast).filter(Broadcast.id == broadcast_id).first()
    
    @staticmethod
    def get_target_users(session: Session, broadcast: Broadcast) -> List[User]:
        """Получить список пользователей для рассылки."""
        query = session.query(User).filter(User.is_blocked == False)
        
        if not broadcast.target_all:
            if broadcast.target_lang:
                query = query.filter(User.language == broadcast.target_lang)
            
            if broadcast.target_has_subscription is not None:
                if broadcast.target_has_subscription:
                    # Пользователи с активными подписками
                    query = query.join(UserSubscription).filter(
                        UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                    )
                else:
                    # Пользователи без активных подписок
                    subquery = session.query(UserSubscription.user_id).filter(
                        UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                    )
                    query = query.filter(~User.id.in_(subquery))
            
            if broadcast.target_channel_id:
                query = query.join(UserSubscription).filter(
                    UserSubscription.channel_id == broadcast.target_channel_id,
                    UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
                )
        
        return query.distinct().all()
    
    @staticmethod
    def update_progress(session: Session, broadcast_id: int, sent: int = 0, failed: int = 0) -> None:
        """Обновить прогресс рассылки."""
        session.query(Broadcast).filter(Broadcast.id == broadcast_id).update({
            "sent_count": Broadcast.sent_count + sent,
            "failed_count": Broadcast.failed_count + failed
        })
    
    @staticmethod
    def mark_completed(session: Session, broadcast_id: int) -> None:
        """Отметить рассылку как завершённую."""
        session.query(Broadcast).filter(Broadcast.id == broadcast_id).update({
            "is_completed": True,
            "completed_at": datetime.utcnow()
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ИНИЦИАЛИЗАЦИЯ ДАННЫХ ПО УМОЛЧАНИЮ
# ═══════════════════════════════════════════════════════════════════════════════

def init_default_data(session: Session) -> None:
    """Инициализация всех данных по умолчанию."""
    print("📦 Инициализация данных по умолчанию...")
    
    # Кнопки меню
    MenuButtonCRUD.init_default_buttons(session)
    print("  ✓ Кнопки меню")
    
    # Тексты бота
    BotTextCRUD.init_default_texts(session)
    print("  ✓ Тексты бота")
    
    session.commit()
    print("✅ Данные по умолчанию инициализированы!")
