"""
═══════════════════════════════════════════════════════════════════════════════
👤 USER HANDLERS PACKAGE
═══════════════════════════════════════════════════════════════════════════════
Пользовательские обработчики.
Этот файл собирает все роутеры из модулей пользователя.

Модули из Chat 3:
- start.py — /start, регистрация, выбор языка
- menu.py — главное меню
- catalog.py — каталог каналов и пакетов
- subscription.py — оформление подписки
- payment.py — оплата
- promo.py — промокоды
- profile.py — профиль пользователя
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router


def get_user_router() -> Router:
    """
    Создание и настройка пользовательского роутера.
    
    Returns:
        Router: Главный роутер с подключёнными обработчиками
    """
    router = Router(name="user")
    
    # Импорт роутеров из модулей
    # Порядок важен! От более специфичных к общим
    
    try:
        from .start import router as start_router
        router.include_router(start_router)
    except ImportError:
        pass
    
    try:
        from .menu import router as menu_router
        router.include_router(menu_router)
    except ImportError:
        pass
    
    try:
        from .catalog import router as catalog_router
        router.include_router(catalog_router)
    except ImportError:
        pass
    
    try:
        from .subscription import router as subscription_router
        router.include_router(subscription_router)
    except ImportError:
        pass
    
    try:
        from .payment import router as payment_router
        router.include_router(payment_router)
    except ImportError:
        pass
    
    try:
        from .promo import router as promo_router
        router.include_router(promo_router)
    except ImportError:
        pass
    
    try:
        from .profile import router as profile_router
        router.include_router(profile_router)
    except ImportError:
        pass
    
    return router


__all__ = ["get_user_router"]
