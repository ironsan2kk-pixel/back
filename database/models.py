"""
═══════════════════════════════════════════════════════════════════════════════
📁 database/models.py — Модели SQLAlchemy
═══════════════════════════════════════════════════════════════════════════════
Все модели базы данных для Telegram бота продажи доступов.
Включает: пользователи, каналы, пакеты, подписки, платежи, промокоды,
конструктор меню, тексты бота, статистика.
═══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime, 
    Float, ForeignKey, Enum, Index, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 БАЗОВЫЙ КЛАСС
# ═══════════════════════════════════════════════════════════════════════════════

Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ПЕРЕЧИСЛЕНИЯ (ENUMS)
# ═══════════════════════════════════════════════════════════════════════════════

class Language(str, PyEnum):
    """Поддерживаемые языки."""
    RU = "ru"
    EN = "en"


class SubscriptionType(str, PyEnum):
    """Тип подписки."""
    CHANNEL = "channel"  # Подписка на отдельный канал
    PACKAGE = "package"  # Подписка на пакет каналов


class SubscriptionStatus(str, PyEnum):
    """Статус подписки."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TRIAL = "trial"


class PaymentStatus(str, PyEnum):
    """Статус платежа."""
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PromocodeType(str, PyEnum):
    """Тип промокода."""
    PERCENT = "percent"      # Скидка в процентах
    FIXED = "fixed"          # Фиксированная скидка
    FREE_DAYS = "free_days"  # Бесплатные дни
    FREE_ACCESS = "free"     # Полностью бесплатный доступ


class MenuButtonType(str, PyEnum):
    """Тип кнопки меню."""
    CATALOG = "catalog"          # Каталог каналов/пакетов (системная)
    PROFILE = "profile"          # Профиль пользователя (системная)
    PROMOCODE = "promocode"      # Ввод промокода (системная)
    SUPPORT = "support"          # Поддержка (системная)
    LANGUAGE = "language"        # Смена языка (системная)
    URL = "url"                  # Внешняя ссылка
    TEXT = "text"                # Текстовое сообщение
    SUBMENU = "submenu"          # Подменю
    CUSTOM = "custom"            # Кастомное действие


# ═══════════════════════════════════════════════════════════════════════════════
# 👤 ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════════════════════

class User(Base):
    """Модель пользователя бота."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language = Column(Enum(Language), default=Language.RU, nullable=False)
    
    # Статусы
    is_blocked = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Статистика
    total_spent = Column(Float, default=0.0, nullable=False)
    referral_code = Column(String(32), unique=True, nullable=True)
    referred_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_activity = Column(DateTime, default=func.now(), nullable=False)
    
    # Связи
    subscriptions = relationship("UserSubscription", back_populates="user", lazy="dynamic")
    payments = relationship("Payment", back_populates="user", lazy="dynamic")
    promocode_usages = relationship("PromocodeUsage", back_populates="user", lazy="dynamic")
    referrals = relationship("User", backref="referrer", remote_side=[id], lazy="dynamic")
    
    def __repr__(self):
        return f"<User {self.telegram_id} ({self.username})>"
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id)
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя (с @username если есть)."""
        if self.username:
            return f"{self.full_name} (@{self.username})"
        return self.full_name


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 КАНАЛЫ
# ═══════════════════════════════════════════════════════════════════════════════

class Channel(Base):
    """Модель канала/группы для продажи доступа."""
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)  # @username канала
    
    # Названия и описания на разных языках
    name_ru = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    description_ru = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    
    # Медиа
    image_url = Column(String(500), nullable=True)  # URL или file_id картинки
    preview_link = Column(String(500), nullable=True)  # Ссылка на превью канала
    
    # Настройки
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Пробный период
    trial_enabled = Column(Boolean, default=False, nullable=False)
    trial_days = Column(Integer, default=1, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    plans = relationship("SubscriptionPlan", back_populates="channel", lazy="dynamic", cascade="all, delete-orphan")
    package_channels = relationship("PackageChannel", back_populates="channel", lazy="dynamic")
    
    def __repr__(self):
        return f"<Channel {self.name_ru} ({self.telegram_id})>"
    
    def get_name(self, lang: str = "ru") -> str:
        """Получить название на нужном языке."""
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name_ru
    
    def get_description(self, lang: str = "ru") -> str:
        """Получить описание на нужном языке."""
        if lang == "en" and self.description_en:
            return self.description_en
        return self.description_ru or ""


# ═══════════════════════════════════════════════════════════════════════════════
# 💰 ТАРИФНЫЕ ПЛАНЫ
# ═══════════════════════════════════════════════════════════════════════════════

class SubscriptionPlan(Base):
    """Тарифный план для канала."""
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    
    # Названия
    name_ru = Column(String(255), nullable=False)  # "7 дней", "1 месяц", "Навсегда"
    name_en = Column(String(255), nullable=True)
    
    # Параметры
    duration_days = Column(Integer, nullable=False)  # 0 = навсегда
    price = Column(Float, nullable=False)  # Цена в USDT
    
    # Старая цена (для отображения скидки)
    old_price = Column(Float, nullable=True)
    
    # Настройки
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    channel = relationship("Channel", back_populates="plans")
    
    def __repr__(self):
        return f"<SubscriptionPlan {self.name_ru} - ${self.price}>"
    
    def get_name(self, lang: str = "ru") -> str:
        """Получить название на нужном языке."""
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name_ru
    
    @property
    def is_lifetime(self) -> bool:
        """Проверка на пожизненную подписку."""
        return self.duration_days == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ПАКЕТЫ ПОДПИСОК
# ═══════════════════════════════════════════════════════════════════════════════

class SubscriptionPackage(Base):
    """Пакет подписок (несколько каналов в одной подписке)."""
    __tablename__ = "subscription_packages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Названия и описания
    name_ru = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    description_ru = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    
    # Медиа
    image_url = Column(String(500), nullable=True)
    
    # Настройки
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Пробный период
    trial_enabled = Column(Boolean, default=False, nullable=False)
    trial_days = Column(Integer, default=1, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    package_channels = relationship("PackageChannel", back_populates="package", lazy="dynamic", cascade="all, delete-orphan")
    plans = relationship("PackagePlan", back_populates="package", lazy="dynamic", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SubscriptionPackage {self.name_ru}>"
    
    def get_name(self, lang: str = "ru") -> str:
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name_ru
    
    def get_description(self, lang: str = "ru") -> str:
        if lang == "en" and self.description_en:
            return self.description_en
        return self.description_ru or ""


class PackageChannel(Base):
    """Связь пакета с каналами (многие-ко-многим)."""
    __tablename__ = "package_channels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(Integer, ForeignKey("subscription_packages.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Связи
    package = relationship("SubscriptionPackage", back_populates="package_channels")
    channel = relationship("Channel", back_populates="package_channels")
    
    # Уникальность пары пакет-канал
    __table_args__ = (
        UniqueConstraint("package_id", "channel_id", name="unique_package_channel"),
    )


class PackagePlan(Base):
    """Тарифный план для пакета."""
    __tablename__ = "package_plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(Integer, ForeignKey("subscription_packages.id", ondelete="CASCADE"), nullable=False)
    
    # Названия
    name_ru = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    
    # Параметры
    duration_days = Column(Integer, nullable=False)  # 0 = навсегда
    price = Column(Float, nullable=False)
    old_price = Column(Float, nullable=True)
    
    # Настройки
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    package = relationship("SubscriptionPackage", back_populates="plans")
    
    def get_name(self, lang: str = "ru") -> str:
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name_ru
    
    @property
    def is_lifetime(self) -> bool:
        return self.duration_days == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ПОДПИСКИ ПОЛЬЗОВАТЕЛЕЙ
# ═══════════════════════════════════════════════════════════════════════════════

class UserSubscription(Base):
    """Подписка пользователя на канал или пакет."""
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Тип подписки
    subscription_type = Column(Enum(SubscriptionType), nullable=False)
    
    # Ссылка на канал ИЛИ пакет (в зависимости от типа)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    package_id = Column(Integer, ForeignKey("subscription_packages.id", ondelete="SET NULL"), nullable=True)
    
    # Статус и сроки
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # NULL = пожизненная
    
    # Связь с платежом
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    
    # Пробный период
    is_trial = Column(Boolean, default=False, nullable=False)
    
    # Уведомления
    expiry_notified = Column(Boolean, default=False, nullable=False)  # Уведомлён об истечении
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    user = relationship("User", back_populates="subscriptions")
    channel = relationship("Channel")
    package = relationship("SubscriptionPackage")
    payment = relationship("Payment")
    
    # Индексы
    __table_args__ = (
        Index("idx_user_subscription_status", "user_id", "status"),
        Index("idx_subscription_expires", "expires_at", "status"),
    )
    
    def __repr__(self):
        target = self.channel.name_ru if self.channel else self.package.name_ru if self.package else "Unknown"
        return f"<UserSubscription {self.user_id} -> {target}>"
    
    @property
    def is_active(self) -> bool:
        """Проверка активности подписки."""
        if self.status != SubscriptionStatus.ACTIVE and self.status != SubscriptionStatus.TRIAL:
            return False
        if self.expires_at is None:
            return True  # Пожизненная
        return datetime.utcnow() < self.expires_at
    
    @property
    def is_lifetime(self) -> bool:
        """Проверка на пожизненную подписку."""
        return self.expires_at is None
    
    @property
    def days_left(self) -> Optional[int]:
        """Дней до истечения."""
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)


# ═══════════════════════════════════════════════════════════════════════════════
# 💳 ПЛАТЕЖИ
# ═══════════════════════════════════════════════════════════════════════════════

class Payment(Base):
    """Платёж через Crypto Bot."""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Crypto Bot данные
    invoice_id = Column(BigInteger, unique=True, nullable=False)  # ID инвойса в Crypto Bot
    invoice_hash = Column(String(255), nullable=True)  # Hash для проверки
    
    # Сумма
    amount = Column(Float, nullable=False)  # Сумма в USDT
    original_amount = Column(Float, nullable=True)  # Оригинальная сумма (до скидки)
    
    # Промокод
    promocode_id = Column(Integer, ForeignKey("promocodes.id", ondelete="SET NULL"), nullable=True)
    discount_amount = Column(Float, default=0.0, nullable=False)  # Размер скидки
    
    # Что покупается
    subscription_type = Column(Enum(SubscriptionType), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    package_id = Column(Integer, ForeignKey("subscription_packages.id", ondelete="SET NULL"), nullable=True)
    plan_id = Column(Integer, nullable=True)  # ID плана (канала или пакета)
    duration_days = Column(Integer, nullable=False)
    
    # Статус
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    paid_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Когда истечёт инвойс
    
    # Дополнительные данные
    crypto_currency = Column(String(10), nullable=True)  # BTC, ETH, USDT и т.д.
    pay_url = Column(String(500), nullable=True)  # Ссылка на оплату
    
    # Связи
    user = relationship("User", back_populates="payments")
    promocode = relationship("Promocode")
    channel = relationship("Channel")
    package = relationship("SubscriptionPackage")
    
    # Индексы
    __table_args__ = (
        Index("idx_payment_status", "status"),
        Index("idx_payment_user", "user_id", "status"),
    )
    
    def __repr__(self):
        return f"<Payment {self.invoice_id} - ${self.amount} ({self.status.value})>"


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ПРОМОКОДЫ
# ═══════════════════════════════════════════════════════════════════════════════

class Promocode(Base):
    """Промокод для скидок и бесплатного доступа."""
    __tablename__ = "promocodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Код
    code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Тип и значение
    type = Column(Enum(PromocodeType), nullable=False)
    value = Column(Float, nullable=False)  # Процент, сумма или дни в зависимости от типа
    
    # Ограничения
    max_uses = Column(Integer, nullable=True)  # NULL = безлимитный
    current_uses = Column(Integer, default=0, nullable=False)
    
    # Привязка к каналу/пакету (NULL = для всего)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    package_id = Column(Integer, ForeignKey("subscription_packages.id", ondelete="SET NULL"), nullable=True)
    
    # Срок действия
    valid_from = Column(DateTime, default=func.now(), nullable=False)
    valid_until = Column(DateTime, nullable=True)  # NULL = бессрочный
    
    # Настройки
    is_active = Column(Boolean, default=True, nullable=False)
    one_per_user = Column(Boolean, default=True, nullable=False)  # Только 1 раз на пользователя
    
    # Для какого плана (опционально)
    min_plan_price = Column(Float, nullable=True)  # Минимальная цена плана
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    channel = relationship("Channel")
    package = relationship("SubscriptionPackage")
    usages = relationship("PromocodeUsage", back_populates="promocode", lazy="dynamic")
    
    def __repr__(self):
        return f"<Promocode {self.code} ({self.type.value})>"
    
    @property
    def is_valid(self) -> bool:
        """Проверка валидности промокода."""
        if not self.is_active:
            return False
        
        now = datetime.utcnow()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        
        return True
    
    @property
    def uses_left(self) -> Optional[int]:
        """Осталось использований."""
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.current_uses)
    
    def calculate_discount(self, original_price: float) -> float:
        """Рассчитать скидку для цены."""
        if self.type == PromocodeType.PERCENT:
            return original_price * (self.value / 100)
        elif self.type == PromocodeType.FIXED:
            return min(self.value, original_price)
        elif self.type == PromocodeType.FREE_ACCESS:
            return original_price
        return 0.0


class PromocodeUsage(Base):
    """Использование промокода пользователем."""
    __tablename__ = "promocode_usages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    promocode_id = Column(Integer, ForeignKey("promocodes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    
    used_at = Column(DateTime, default=func.now(), nullable=False)
    discount_amount = Column(Float, nullable=False)  # Сколько сэкономил пользователь
    
    # Связи
    promocode = relationship("Promocode", back_populates="usages")
    user = relationship("User", back_populates="promocode_usages")
    payment = relationship("Payment")
    
    # Уникальность (если one_per_user)
    __table_args__ = (
        Index("idx_promocode_user", "promocode_id", "user_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🏗️ КОНСТРУКТОР МЕНЮ
# ═══════════════════════════════════════════════════════════════════════════════

class MenuButton(Base):
    """Кнопка меню бота (конструктор)."""
    __tablename__ = "menu_buttons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Идентификатор
    button_key = Column(String(50), unique=True, nullable=False)  # catalog, profile, custom_1
    
    # Тип кнопки
    button_type = Column(Enum(MenuButtonType), nullable=False)
    
    # Тексты
    text_ru = Column(String(100), nullable=False)  # "📢 Каталог"
    text_en = Column(String(100), nullable=True)
    
    # Контент (в зависимости от типа)
    url = Column(String(500), nullable=True)  # Для URL кнопок
    content_ru = Column(Text, nullable=True)  # Текст сообщения для TEXT кнопок
    content_en = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)  # Картинка для сообщения
    
    # Иерархия
    parent_id = Column(Integer, ForeignKey("menu_buttons.id", ondelete="SET NULL"), nullable=True)
    
    # Настройки
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)  # Системные нельзя удалить
    sort_order = Column(Integer, default=0, nullable=False)
    row = Column(Integer, default=0, nullable=False)  # Ряд в клавиатуре
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    children = relationship("MenuButton", backref="parent", remote_side=[id], lazy="dynamic")
    
    def __repr__(self):
        return f"<MenuButton {self.button_key} ({self.button_type.value})>"
    
    def get_text(self, lang: str = "ru") -> str:
        """Получить текст на нужном языке."""
        if lang == "en" and self.text_en:
            return self.text_en
        return self.text_ru
    
    def get_content(self, lang: str = "ru") -> str:
        """Получить контент на нужном языке."""
        if lang == "en" and self.content_en:
            return self.content_en
        return self.content_ru or ""


# ═══════════════════════════════════════════════════════════════════════════════
# 📝 ТЕКСТЫ БОТА
# ═══════════════════════════════════════════════════════════════════════════════

class BotText(Base):
    """Тексты бота (редактируемые через админку)."""
    __tablename__ = "bot_texts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Ключ текста
    text_key = Column(String(100), unique=True, nullable=False, index=True)  # welcome, subscription_expired
    
    # Описание (для админки)
    description = Column(String(255), nullable=True)
    
    # Тексты на разных языках
    text_ru = Column(Text, nullable=False)
    text_en = Column(Text, nullable=True)
    
    # Переменные которые можно использовать
    variables = Column(JSON, nullable=True)  # ["user_name", "channel_name", "days_left"]
    
    # Настройки
    is_system = Column(Boolean, default=False, nullable=False)  # Системные нельзя удалить
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<BotText {self.text_key}>"
    
    def get_text(self, lang: str = "ru", **kwargs) -> str:
        """Получить текст с подстановкой переменных."""
        if lang == "en" and self.text_en:
            text = self.text_en
        else:
            text = self.text_ru
        
        # Подстановка переменных
        for key, value in kwargs.items():
            text = text.replace(f"{{{key}}}", str(value))
        
        return text


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 СТАТИСТИКА И ЛОГИ
# ═══════════════════════════════════════════════════════════════════════════════

class DailyStats(Base):
    """Ежедневная статистика."""
    __tablename__ = "daily_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Пользователи
    new_users = Column(Integer, default=0, nullable=False)
    active_users = Column(Integer, default=0, nullable=False)
    total_users = Column(Integer, default=0, nullable=False)
    
    # Подписки
    new_subscriptions = Column(Integer, default=0, nullable=False)
    expired_subscriptions = Column(Integer, default=0, nullable=False)
    active_subscriptions = Column(Integer, default=0, nullable=False)
    
    # Платежи
    payments_count = Column(Integer, default=0, nullable=False)
    payments_amount = Column(Float, default=0.0, nullable=False)
    
    # Промокоды
    promocodes_used = Column(Integer, default=0, nullable=False)
    discounts_total = Column(Float, default=0.0, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)


class ActivityLog(Base):
    """Лог активности для аналитики."""
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    # Действие
    action = Column(String(50), nullable=False)  # start, buy, subscribe, kick
    details = Column(JSON, nullable=True)  # Дополнительные данные
    
    # Временная метка
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Индексы
    __table_args__ = (
        Index("idx_activity_action", "action", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 📨 РАССЫЛКА
# ═══════════════════════════════════════════════════════════════════════════════

class Broadcast(Base):
    """Рассылка сообщений пользователям."""
    __tablename__ = "broadcasts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Текст рассылки
    text_ru = Column(Text, nullable=False)
    text_en = Column(Text, nullable=True)
    
    # Медиа
    image_url = Column(String(500), nullable=True)
    
    # Кнопки (JSON)
    buttons = Column(JSON, nullable=True)  # [{"text": "Купить", "url": "..."}]
    
    # Фильтры получателей
    target_all = Column(Boolean, default=True, nullable=False)
    target_lang = Column(String(2), nullable=True)  # ru/en или NULL для всех
    target_has_subscription = Column(Boolean, nullable=True)  # NULL = все
    target_channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    
    # Статистика
    total_users = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    
    # Статус
    is_completed = Column(Boolean, default=False, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Создатель
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ НАСТРОЙКИ БОТА
# ═══════════════════════════════════════════════════════════════════════════════

class BotSettings(Base):
    """Глобальные настройки бота."""
    __tablename__ = "bot_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string", nullable=False)  # string, int, bool, json
    description = Column(String(255), nullable=True)
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    @property
    def typed_value(self):
        """Получить значение с правильным типом."""
        if self.value is None:
            return None
        
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        return self.value


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_models():
    """Получить список всех моделей."""
    return [
        User,
        Channel,
        SubscriptionPlan,
        SubscriptionPackage,
        PackageChannel,
        PackagePlan,
        UserSubscription,
        Payment,
        Promocode,
        PromocodeUsage,
        MenuButton,
        BotText,
        DailyStats,
        ActivityLog,
        Broadcast,
        BotSettings,
    ]
