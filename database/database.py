"""
═══════════════════════════════════════════════════════════════════════════════
📁 database/database.py — Подключение к базе данных (Async)
═══════════════════════════════════════════════════════════════════════════════
Инициализация асинхронного SQLAlchemy, управление сессиями, создание таблиц.
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy import event, text

# Добавляем родительскую директорию в путь для импорта config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from database.models import Base


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ═══════════════════════════════════════════════════════════════════════════════

engine: Optional[AsyncEngine] = None
async_session: Optional[async_sessionmaker[AsyncSession]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 🏗️ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ═══════════════════════════════════════════════════════════════════════════════

async def init_db() -> None:
    """
    Инициализация базы данных - создание движка, сессий и таблиц.
    """
    global engine, async_session
    
    # Создание асинхронного движка
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
    
    # Фабрика асинхронных сессий
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("[OK] База данных инициализирована")


async def close_db() -> None:
    """
    Закрытие соединения с базой данных.
    """
    global engine
    
    if engine:
        await engine.dispose()
        print("[OK] Соединение с БД закрыто")


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ПОЛУЧЕНИЕ СЕССИИ
# ═══════════════════════════════════════════════════════════════════════════════

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий.
    
    Использование:
        async with get_session() as session:
            result = await session.execute(...)
    """
    global async_session
    
    if async_session is None:
        await init_db()
    
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════════════════

async def check_connection() -> bool:
    """
    Проверка подключения к базе данных.
    
    Returns:
        True если подключение успешно.
    """
    global engine
    
    if engine is None:
        return False
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка подключения к БД: {e}")
        return False


async def get_database_stats() -> dict:
    """
    Получить статистику базы данных.
    """
    from sqlalchemy import func, select
    from database.models import User, Channel, Payment, UserSubscription, Promocode
    
    stats = {}
    
    async with async_session() as session:
        # Пользователи
        result = await session.execute(select(func.count(User.id)))
        stats["users_total"] = result.scalar() or 0
        
        result = await session.execute(
            select(func.count(User.id)).where(User.is_blocked == False)
        )
        stats["users_active"] = result.scalar() or 0
        
        # Каналы
        result = await session.execute(select(func.count(Channel.id)))
        stats["channels_total"] = result.scalar() or 0
        
        result = await session.execute(
            select(func.count(Channel.id)).where(Channel.is_active == True)
        )
        stats["channels_active"] = result.scalar() or 0
        
        # Подписки
        result = await session.execute(
            select(func.count(UserSubscription.id)).where(UserSubscription.status == "active")
        )
        stats["subscriptions_active"] = result.scalar() or 0
        
        # Платежи
        result = await session.execute(select(func.count(Payment.id)))
        stats["payments_total"] = result.scalar() or 0
        
        result = await session.execute(
            select(func.count(Payment.id)).where(Payment.status == "paid")
        )
        stats["payments_paid"] = result.scalar() or 0
        
        # Промокоды
        result = await session.execute(select(func.count(Promocode.id)))
        stats["promocodes_total"] = result.scalar() or 0
        
        result = await session.execute(
            select(func.count(Promocode.id)).where(Promocode.is_active == True)
        )
        stats["promocodes_active"] = result.scalar() or 0
    
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 ТЕСТИРОВАНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("\n[*] Проверка подключения к базе данных...\n")
        
        await init_db()
        
        if await check_connection():
            print("[OK] Подключение успешно!")
            print(f"[INFO] URL БД: {settings.DATABASE_URL}")
            
            # Вывод статистики
            print("\n[INFO] Статистика БД:")
            stats = await get_database_stats()
            for key, value in stats.items():
                print(f"  - {key}: {value}")
        else:
            print("[ERROR] Не удалось подключиться к базе данных!")
        
        await close_db()
    
    asyncio.run(main())
