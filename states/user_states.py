"""
═══════════════════════════════════════════════════════════════════════════════
🔄 СОСТОЯНИЯ FSM ДЛЯ ПОЛЬЗОВАТЕЛЯ
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram.fsm.state import State, StatesGroup


class LanguageState(StatesGroup):
    """Состояния выбора языка."""
    selecting = State()


class PromoState(StatesGroup):
    """Состояния ввода промокода."""
    waiting_code = State()


class SubscriptionState(StatesGroup):
    """Состояния оформления подписки."""
    selecting_channel = State()
    selecting_package = State()
    selecting_period = State()
    confirming = State()
    waiting_payment = State()


class SupportState(StatesGroup):
    """Состояния обращения в поддержку."""
    waiting_message = State()


class FeedbackState(StatesGroup):
    """Состояния отправки отзыва."""
    waiting_feedback = State()
