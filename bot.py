"""
═══════════════════════════════════════════════════════════════════════════════
🤖 TELEGRAM БОТ ПРОДАЖИ ДОСТУПОВ К КАНАЛАМ
═══════════════════════════════════════════════════════════════════════════════
Главная точка входа для запуска бота.

Функционал:
- Инициализация бота и диспетчера
- Подключение всех роутеров (user + admin)
- Регистрация middleware
- Запуск планировщика задач
- Graceful shutdown

Запуск: python bot.py
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from config import settings
from database.database import init_db, close_db, async_session
from database.crud import UserCRUD

# Middleware imports
from middlewares.i18n import I18nMiddleware
from middlewares.database import DatabaseMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.logging import LoggingMiddleware

# Handler imports
from handlers.user import get_user_router
from handlers.admin import get_admin_router

# Scheduler
from scheduler.tasks import start_scheduler, stop_scheduler

# ═══════════════════════════════════════════════════════════════════════════════
# 📝 НАСТРОЙКА ЛОГИРОВАНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

def setup_logging() -> None:
    """Настройка системы логирования."""
    # Создаём папку для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Формат логов
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Настройка корневого логгера
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Файл с ротацией по дням
            logging.FileHandler(
                log_dir / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log",
                encoding="utf-8"
            ),
            # Консольный вывод
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Уменьшаем уровень логов для библиотек
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    
    # Наш логгер
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("🚀 Логирование инициализировано")
    logger.info(f"📁 Логи сохраняются в: {log_dir.absolute()}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🤖 ИНИЦИАЛИЗАЦИЯ БОТА
# ═══════════════════════════════════════════════════════════════════════════════

async def create_bot() -> Bot:
    """Создание экземпляра бота."""
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True
        )
    )
    return bot


async def create_dispatcher() -> Dispatcher:
    """Создание диспетчера с настройками."""
    # Хранилище состояний (в памяти)
    # Для production можно использовать Redis
    storage = MemoryStorage()
    
    dp = Dispatcher(storage=storage)
    return dp


# ═══════════════════════════════════════════════════════════════════════════════
# 🔌 РЕГИСТРАЦИЯ MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

def register_middlewares(dp: Dispatcher) -> None:
    """Регистрация всех middleware."""
    logger = logging.getLogger(__name__)
    
    # Порядок важен! Выполняются сверху вниз
    
    # 1. Логирование (первый - логирует все запросы)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    logger.info("✅ LoggingMiddleware зарегистрирован")
    
    # 2. Throttling (защита от спама)
    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.3))
    logger.info("✅ ThrottlingMiddleware зарегистрирован")
    
    # 3. База данных (сессия для каждого запроса)
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    logger.info("✅ DatabaseMiddleware зарегистрирован")
    
    # 4. Интернационализация (последний - использует данные из БД)
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())
    logger.info("✅ I18nMiddleware зарегистрирован")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 РЕГИСТРАЦИЯ РОУТЕРОВ
# ═══════════════════════════════════════════════════════════════════════════════

def register_routers(dp: Dispatcher) -> None:
    """Регистрация всех роутеров."""
    logger = logging.getLogger(__name__)
    
    # Пользовательский роутер
    user_router = get_user_router()
    dp.include_router(user_router)
    logger.info("✅ User Router зарегистрирован")
    
    # Админский роутер
    admin_router = get_admin_router()
    dp.include_router(admin_router)
    logger.info("✅ Admin Router зарегистрирован")


# ═══════════════════════════════════════════════════════════════════════════════
# 📜 НАСТРОЙКА КОМАНД БОТА
# ═══════════════════════════════════════════════════════════════════════════════

async def setup_bot_commands(bot: Bot) -> None:
    """Установка команд бота в меню."""
    logger = logging.getLogger(__name__)
    
    # Команды для всех пользователей
    user_commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="catalog", description="📢 Каталог каналов"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="support", description="💬 Поддержка"),
        BotCommand(command="language", description="🌐 Сменить язык"),
    ]
    
    # Устанавливаем команды для всех
    await bot.set_my_commands(
        commands=user_commands,
        scope=BotCommandScopeDefault()
    )
    logger.info(f"✅ Установлено {len(user_commands)} команд для пользователей")
    
    # Дополнительные команды для админов
    admin_commands = user_commands + [
        BotCommand(command="admin", description="🔐 Админ-панель"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="broadcast", description="📨 Рассылка"),
    ]
    
    # Устанавливаем команды для каждого админа
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.set_my_commands(
                commands=admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
            logger.info(f"✅ Установлены админ-команды для ID: {admin_id}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось установить команды для админа {admin_id}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔔 УВЕДОМЛЕНИЯ АДМИНАМ
# ═══════════════════════════════════════════════════════════════════════════════

async def notify_admins(bot: Bot, message: str) -> None:
    """Отправка уведомления всем админам."""
    logger = logging.getLogger(__name__)
    
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления админу {admin_id}: {e}")


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота."""
    logger = logging.getLogger(__name__)
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username} (ID: {bot_info.id})")
    
    # Уведомляем админов
    startup_text = (
        "🟢 <b>Бот запущен!</b>\n\n"
        f"🤖 @{bot_info.username}\n"
        f"🆔 ID: <code>{bot_info.id}</code>\n"
        f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        f"✅ Все системы работают"
    )
    await notify_admins(bot, startup_text)


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота."""
    logger = logging.getLogger(__name__)
    
    # Получаем информацию о боте
    try:
        bot_info = await bot.get_me()
        
        # Уведомляем админов
        shutdown_text = (
            "🔴 <b>Бот остановлен!</b>\n\n"
            f"🤖 @{bot_info.username}\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        await notify_admins(bot, shutdown_text)
    except Exception as e:
        logger.error(f"❌ Ошибка при shutdown: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
# ═══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    """Главная функция запуска бота."""
    logger = logging.getLogger(__name__)
    
    # Настройка логирования
    setup_logging()
    logger.info("🚀 Запуск бота...")
    
    # Проверка конфигурации
    if not settings.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен в .env файле!")
        sys.exit(1)
    
    if not settings.CRYPTO_BOT_TOKEN:
        logger.warning("⚠️ CRYPTO_BOT_TOKEN не установлен - платежи не будут работать")
    
    if not settings.ADMIN_IDS:
        logger.warning("⚠️ ADMIN_IDS не установлены - админ-панель будет недоступна")
    
    # Инициализация базы данных
    logger.info("📊 Инициализация базы данных...")
    await init_db()
    logger.info("✅ База данных готова")
    
    # Создание бота и диспетчера
    bot = await create_bot()
    dp = await create_dispatcher()
    
    # Регистрация middleware и роутеров
    register_middlewares(dp)
    register_routers(dp)
    
    # Установка команд
    await setup_bot_commands(bot)
    
    # Запуск планировщика
    logger.info("⏰ Запуск планировщика задач...")
    scheduler = await start_scheduler(bot)
    logger.info("✅ Планировщик запущен")
    
    # Регистрация startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        logger.info("=" * 60)
        logger.info("🟢 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ")
        logger.info("=" * 60)
        
        # Удаляем webhook и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            close_bot_session=False
        )
        
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")
        raise
        
    finally:
        logger.info("🔄 Завершение работы...")
        
        # Останавливаем планировщик
        await stop_scheduler(scheduler)
        logger.info("✅ Планировщик остановлен")
        
        # Закрываем базу данных
        await close_db()
        logger.info("✅ База данных закрыта")
        
        # Закрываем сессию бота
        await bot.session.close()
        logger.info("✅ Сессия бота закрыта")
        
        logger.info("=" * 60)
        logger.info("🔴 БОТ ОСТАНОВЛЕН")
        logger.info("=" * 60)


# ═══════════════════════════════════════════════════════════════════════════════
# 🏁 ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Обработка сигналов для graceful shutdown
    if sys.platform != "win32":
        # Unix-like systems
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
