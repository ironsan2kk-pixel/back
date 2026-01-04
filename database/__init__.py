"""
═══════════════════════════════════════════════════════════════════════════════
🗄️ DATABASE PACKAGE
═══════════════════════════════════════════════════════════════════════════════
Компоненты для работы с базой данных.

Из Chat 2:
- database.py — подключение и сессии
- models.py — SQLAlchemy модели
- crud.py — CRUD операции
═══════════════════════════════════════════════════════════════════════════════
"""

try:
    from .database import init_db, close_db, async_session, get_session
except ImportError:
    init_db = None
    close_db = None
    async_session = None
    get_session = None

try:
    from .crud import (
        UserCRUD,
        ChannelCRUD,
        PackageCRUD,
        SubscriptionCRUD,
        PaymentCRUD,
        PromoCRUD,
        SettingsCRUD,
        StatsCRUD,
        BroadcastCRUD,
        PromoUsageCRUD,
    )
except ImportError:
    UserCRUD = None
    ChannelCRUD = None
    PackageCRUD = None
    SubscriptionCRUD = None
    PaymentCRUD = None
    PromoCRUD = None
    SettingsCRUD = None
    StatsCRUD = None
    BroadcastCRUD = None
    PromoUsageCRUD = None

__all__ = [
    "init_db",
    "close_db",
    "async_session",
    "get_session",
    "UserCRUD",
    "ChannelCRUD",
    "PackageCRUD",
    "SubscriptionCRUD",
    "PaymentCRUD",
    "PromoCRUD",
    "SettingsCRUD",
    "StatsCRUD",
    "BroadcastCRUD",
    "PromoUsageCRUD",
]
