"""
═══════════════════════════════════════════════════════════════════════════════
🔐 ADMIN HANDLERS PACKAGE
═══════════════════════════════════════════════════════════════════════════════
Административные обработчики.
Этот файл собирает все роутеры из модулей админки.

Модули из Chat 5.1:
- main.py — главное меню админки
- channels.py — управление каналами
- packages.py — управление пакетами
- pricing.py — управление тарифами

Модули из Chat 5.2:
- promos.py — управление промокодами
- users.py — управление пользователями
- stats.py — статистика
- broadcast.py — рассылка
- settings.py — настройки
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery

from config import settings


class AdminFilter(Filter):
    """Фильтр для проверки прав администратора."""
    
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        """Проверка, является ли пользователь админом."""
        user_id = event.from_user.id if event.from_user else None
        return user_id in settings.ADMIN_IDS


def get_admin_router() -> Router:
    """
    Создание и настройка административного роутера.
    
    Returns:
        Router: Главный роутер с подключёнными обработчиками
    """
    router = Router(name="admin")
    
    # Применяем фильтр админа ко всему роутеру
    router.message.filter(AdminFilter())
    router.callback_query.filter(AdminFilter())
    
    # Импорт роутеров из модулей
    # Chat 5.1 - основа админки
    try:
        from .main import router as main_router
        router.include_router(main_router)
    except ImportError:
        pass
    
    try:
        from .channels import router as channels_router
        router.include_router(channels_router)
    except ImportError:
        pass
    
    try:
        from .packages import router as packages_router
        router.include_router(packages_router)
    except ImportError:
        pass
    
    try:
        from .pricing import router as pricing_router
        router.include_router(pricing_router)
    except ImportError:
        pass
    
    # Chat 5.2 - расширенные функции
    try:
        from .promos import router as promos_router
        router.include_router(promos_router)
    except ImportError:
        pass
    
    try:
        from .users import router as users_router
        router.include_router(users_router)
    except ImportError:
        pass
    
    try:
        from .stats import router as stats_router
        router.include_router(stats_router)
    except ImportError:
        pass
    
    try:
        from .broadcast import router as broadcast_router
        router.include_router(broadcast_router)
    except ImportError:
        pass
    
    try:
        from .settings import router as settings_router
        router.include_router(settings_router)
    except ImportError:
        pass
    
    return router


__all__ = ["get_admin_router", "AdminFilter"]
