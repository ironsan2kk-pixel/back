"""
═══════════════════════════════════════════════════════════════════════════════
⚡ SERVICES PACKAGE
═══════════════════════════════════════════════════════════════════════════════
Сервисные компоненты для бизнес-логики.

Из Chat 4:
- crypto_bot.py — интеграция с Crypto Bot API
- channel_manager.py — управление каналами
- subscription_manager.py — управление подписками
- payment_processor.py — обработка платежей
═══════════════════════════════════════════════════════════════════════════════
"""

try:
    from .crypto_bot import CryptoBotAPI
except ImportError:
    CryptoBotAPI = None

try:
    from .channel_manager import ChannelManager
except ImportError:
    ChannelManager = None

try:
    from .subscription_manager import SubscriptionManager
except ImportError:
    SubscriptionManager = None

try:
    from .payment_processor import PaymentProcessor
except ImportError:
    PaymentProcessor = None

__all__ = [
    "CryptoBotAPI",
    "ChannelManager",
    "SubscriptionManager",
    "PaymentProcessor",
]
