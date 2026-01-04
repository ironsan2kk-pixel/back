"""
═══════════════════════════════════════════════════════════════════════════════
⏰ ПЛАНИРОВЩИК АВТОМАТИЧЕСКИХ ЗАДАЧ
═══════════════════════════════════════════════════════════════════════════════
Автоматические задачи:
- Проверка истёкших подписок
- Автокик из каналов
- Уведомления об истечении подписки
- Очистка старых данных
- Отложенная рассылка
- Статистика и отчёты
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from aiogram import Bot
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from database.database import async_session
from database.crud import (
    UserCRUD,
    SubscriptionCRUD,
    ChannelCRUD,
    PaymentCRUD,
    BroadcastCRUD,
    StatsCRUD,
    SettingsCRUD,
)
from services.channel_manager import ChannelManager
from utils.i18n import get_text

logger = logging.getLogger(__name__)

# Глобальная переменная для бота (устанавливается при запуске)
_bot: Optional[Bot] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ИНИЦИАЛИЗАЦИЯ ПЛАНИРОВЩИКА
# ═══════════════════════════════════════════════════════════════════════════════

async def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Запуск планировщика задач."""
    global _bot
    _bot = bot
    
    scheduler = AsyncIOScheduler(
        timezone="UTC",
        job_defaults={
            "coalesce": True,  # Объединять пропущенные задачи
            "max_instances": 1,  # Только один экземпляр задачи
            "misfire_grace_time": 60 * 5,  # 5 минут на выполнение
        }
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # 📋 РЕГИСТРАЦИЯ ЗАДАЧ
    # ─────────────────────────────────────────────────────────────────────────
    
    # 1. Проверка истёкших подписок - каждые 5 минут
    scheduler.add_job(
        check_expired_subscriptions,
        trigger=IntervalTrigger(minutes=5),
        id="check_expired_subscriptions",
        name="Проверка истёкших подписок",
        replace_existing=True
    )
    logger.info("📌 Задача: check_expired_subscriptions (каждые 5 мин)")
    
    # 2. Уведомления об истечении - каждый час
    scheduler.add_job(
        send_expiration_notifications,
        trigger=IntervalTrigger(hours=1),
        id="send_expiration_notifications",
        name="Уведомления об истечении",
        replace_existing=True
    )
    logger.info("📌 Задача: send_expiration_notifications (каждый час)")
    
    # 3. Обработка отложенных рассылок - каждую минуту
    scheduler.add_job(
        process_scheduled_broadcasts,
        trigger=IntervalTrigger(minutes=1),
        id="process_scheduled_broadcasts",
        name="Отложенные рассылки",
        replace_existing=True
    )
    logger.info("📌 Задача: process_scheduled_broadcasts (каждую минуту)")
    
    # 4. Ежедневная статистика - в 00:05 UTC
    scheduler.add_job(
        generate_daily_stats,
        trigger=CronTrigger(hour=0, minute=5),
        id="generate_daily_stats",
        name="Ежедневная статистика",
        replace_existing=True
    )
    logger.info("📌 Задача: generate_daily_stats (00:05 UTC)")
    
    # 5. Еженедельный отчёт админам - понедельник 09:00 UTC
    scheduler.add_job(
        send_weekly_report,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="send_weekly_report",
        name="Еженедельный отчёт",
        replace_existing=True
    )
    logger.info("📌 Задача: send_weekly_report (понедельник 09:00 UTC)")
    
    # 6. Очистка старых логов - каждый день в 03:00 UTC
    scheduler.add_job(
        cleanup_old_data,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_old_data",
        name="Очистка старых данных",
        replace_existing=True
    )
    logger.info("📌 Задача: cleanup_old_data (03:00 UTC)")
    
    # 7. Проверка неоплаченных инвойсов - каждые 30 минут
    scheduler.add_job(
        check_pending_payments,
        trigger=IntervalTrigger(minutes=30),
        id="check_pending_payments",
        name="Проверка неоплаченных инвойсов",
        replace_existing=True
    )
    logger.info("📌 Задача: check_pending_payments (каждые 30 мин)")
    
    # 8. Бэкап базы данных - каждый день в 04:00 UTC
    scheduler.add_job(
        backup_database,
        trigger=CronTrigger(hour=4, minute=0),
        id="backup_database",
        name="Бэкап БД",
        replace_existing=True
    )
    logger.info("📌 Задача: backup_database (04:00 UTC)")
    
    # Запускаем планировщик
    scheduler.start()
    logger.info("✅ Планировщик запущен с 8 задачами")
    
    return scheduler


async def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Остановка планировщика."""
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("✅ Планировщик остановлен")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЗАДАЧА 1: ПРОВЕРКА ИСТЁКШИХ ПОДПИСОК
# ═══════════════════════════════════════════════════════════════════════════════

async def check_expired_subscriptions() -> None:
    """
    Проверка и обработка истёкших подписок.
    - Находит подписки с истёкшим сроком
    - Удаляет пользователей из каналов
    - Обновляет статус подписки
    - Отправляет уведомление пользователю
    """
    global _bot
    if not _bot:
        logger.error("❌ Bot не инициализирован")
        return
    
    logger.info("🔍 Проверка истёкших подписок...")
    
    try:
        async with async_session() as session:
            # Получаем все активные подписки с истёкшим сроком
            expired_subscriptions = await SubscriptionCRUD.get_expired(session)
            
            if not expired_subscriptions:
                logger.info("✅ Истёкших подписок не найдено")
                return
            
            logger.info(f"⚠️ Найдено {len(expired_subscriptions)} истёкших подписок")
            
            # Инициализируем менеджер каналов
            channel_manager = ChannelManager(_bot)
            
            processed = 0
            errors = 0
            
            for subscription in expired_subscriptions:
                try:
                    user_id = subscription.user_id
                    channel_id = subscription.channel_id
                    
                    # Получаем данные канала
                    channel = await ChannelCRUD.get_by_id(session, channel_id)
                    if not channel:
                        continue
                    
                    # Получаем данные пользователя
                    user = await UserCRUD.get_by_id(session, user_id)
                    if not user:
                        continue
                    
                    # Удаляем из канала
                    kicked = await channel_manager.kick_user(
                        channel_telegram_id=channel.telegram_id,
                        user_telegram_id=user.telegram_id
                    )
                    
                    if kicked:
                        logger.info(
                            f"🚫 Пользователь {user.telegram_id} удалён из канала "
                            f"{channel.title} (подписка истекла)"
                        )
                    
                    # Обновляем статус подписки
                    await SubscriptionCRUD.set_expired(session, subscription.id)
                    
                    # Отправляем уведомление пользователю
                    try:
                        lang = user.language or "ru"
                        text = get_text(
                            "subscription_expired",
                            lang,
                            channel_name=channel.title
                        )
                        
                        # Добавляем кнопку для продления
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text="🔄 Продлить подписку",
                                callback_data=f"subscribe:channel:{channel_id}"
                            )]
                        ])
                        
                        await _bot.send_message(
                            chat_id=user.telegram_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        logger.warning(
                            f"⚠️ Не удалось отправить уведомление пользователю "
                            f"{user.telegram_id}: {e}"
                        )
                    
                    processed += 1
                    
                    # Небольшая задержка между операциями
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    errors += 1
                    logger.error(f"❌ Ошибка обработки подписки {subscription.id}: {e}")
            
            # Коммитим изменения
            await session.commit()
            
            logger.info(
                f"✅ Обработка завершена: {processed} успешно, {errors} ошибок"
            )
            
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка в check_expired_subscriptions: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЗАДАЧА 2: УВЕДОМЛЕНИЯ ОБ ИСТЕЧЕНИИ
# ═══════════════════════════════════════════════════════════════════════════════

async def send_expiration_notifications() -> None:
    """
    Отправка уведомлений о скором истечении подписки.
    - За 3 дня
    - За 1 день
    - За 3 часа
    """
    global _bot
    if not _bot:
        return
    
    logger.info("📨 Отправка уведомлений об истечении...")
    
    # Периоды уведомлений
    notification_periods = [
        (timedelta(days=3), "3_days"),
        (timedelta(days=1), "1_day"),
        (timedelta(hours=3), "3_hours"),
    ]
    
    try:
        async with async_session() as session:
            total_sent = 0
            
            for delta, period_key in notification_periods:
                # Получаем подписки, истекающие в указанный период
                expiring_soon = await SubscriptionCRUD.get_expiring_in(
                    session, 
                    delta,
                    notification_sent=period_key  # Проверяем, что не отправляли
                )
                
                for subscription in expiring_soon:
                    try:
                        user = await UserCRUD.get_by_id(session, subscription.user_id)
                        channel = await ChannelCRUD.get_by_id(session, subscription.channel_id)
                        
                        if not user or not channel:
                            continue
                        
                        # Формируем текст уведомления
                        lang = user.language or "ru"
                        
                        if period_key == "3_days":
                            text = get_text(
                                "subscription_expires_3_days",
                                lang,
                                channel_name=channel.title,
                                expires_at=subscription.expires_at.strftime("%d.%m.%Y")
                            )
                        elif period_key == "1_day":
                            text = get_text(
                                "subscription_expires_1_day",
                                lang,
                                channel_name=channel.title
                            )
                        else:  # 3_hours
                            text = get_text(
                                "subscription_expires_soon",
                                lang,
                                channel_name=channel.title,
                                hours=3
                            )
                        
                        # Кнопка продления
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text="🔄 Продлить сейчас",
                                callback_data=f"extend:subscription:{subscription.id}"
                            )]
                        ])
                        
                        await _bot.send_message(
                            chat_id=user.telegram_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML
                        )
                        
                        # Отмечаем, что уведомление отправлено
                        await SubscriptionCRUD.mark_notification_sent(
                            session,
                            subscription.id,
                            period_key
                        )
                        
                        total_sent += 1
                        await asyncio.sleep(0.05)  # Защита от флуда
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка отправки уведомления: {e}")
            
            await session.commit()
            
            if total_sent > 0:
                logger.info(f"✅ Отправлено {total_sent} уведомлений об истечении")
                
    except Exception as e:
        logger.exception(f"❌ Ошибка в send_expiration_notifications: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЗАДАЧА 3: ОБРАБОТКА ОТЛОЖЕННЫХ РАССЫЛОК
# ═══════════════════════════════════════════════════════════════════════════════

async def process_scheduled_broadcasts() -> None:
    """Обработка отложенных рассылок."""
    global _bot
    if not _bot:
        return
    
    try:
        async with async_session() as session:
            # Получаем рассылки, которые пора отправить
            pending_broadcasts = await BroadcastCRUD.get_pending_scheduled(session)
            
            for broadcast in pending_broadcasts:
                try:
                    logger.info(f"📨 Запуск рассылки #{broadcast.id}")
                    
                    # Получаем целевых пользователей
                    target_users = await get_broadcast_targets(
                        session,
                        broadcast.target_type,
                        broadcast.target_filter
                    )
                    
                    if not target_users:
                        logger.warning(f"⚠️ Рассылка #{broadcast.id}: нет целевых пользователей")
                        await BroadcastCRUD.update_status(
                            session, broadcast.id, "completed", 0, 0
                        )
                        continue
                    
                    # Обновляем статус на "в процессе"
                    await BroadcastCRUD.update_status(
                        session, broadcast.id, "processing"
                    )
                    
                    sent_count = 0
                    error_count = 0
                    
                    for user in target_users:
                        try:
                            # Отправляем сообщение
                            if broadcast.media_type == "photo" and broadcast.media_file_id:
                                await _bot.send_photo(
                                    chat_id=user.telegram_id,
                                    photo=broadcast.media_file_id,
                                    caption=broadcast.text,
                                    parse_mode=ParseMode.HTML
                                )
                            elif broadcast.media_type == "video" and broadcast.media_file_id:
                                await _bot.send_video(
                                    chat_id=user.telegram_id,
                                    video=broadcast.media_file_id,
                                    caption=broadcast.text,
                                    parse_mode=ParseMode.HTML
                                )
                            elif broadcast.media_type == "document" and broadcast.media_file_id:
                                await _bot.send_document(
                                    chat_id=user.telegram_id,
                                    document=broadcast.media_file_id,
                                    caption=broadcast.text,
                                    parse_mode=ParseMode.HTML
                                )
                            else:
                                await _bot.send_message(
                                    chat_id=user.telegram_id,
                                    text=broadcast.text,
                                    parse_mode=ParseMode.HTML
                                )
                            
                            sent_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            logger.debug(f"❌ Ошибка отправки пользователю {user.telegram_id}: {e}")
                        
                        # Задержка между сообщениями
                        await asyncio.sleep(0.05)
                    
                    # Обновляем статус
                    await BroadcastCRUD.update_status(
                        session, 
                        broadcast.id, 
                        "completed",
                        sent_count,
                        error_count
                    )
                    
                    logger.info(
                        f"✅ Рассылка #{broadcast.id} завершена: "
                        f"{sent_count} отправлено, {error_count} ошибок"
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка рассылки #{broadcast.id}: {e}")
                    await BroadcastCRUD.update_status(
                        session, broadcast.id, "failed"
                    )
            
            await session.commit()
            
    except Exception as e:
        logger.exception(f"❌ Ошибка в process_scheduled_broadcasts: {e}")


async def get_broadcast_targets(
    session,
    target_type: str,
    target_filter: Optional[dict] = None
) -> List:
    """Получение целевых пользователей для рассылки."""
    
    if target_type == "all":
        return await UserCRUD.get_all_active(session)
    
    elif target_type == "subscribers":
        return await UserCRUD.get_with_active_subscriptions(session)
    
    elif target_type == "non_subscribers":
        return await UserCRUD.get_without_subscriptions(session)
    
    elif target_type == "expired":
        return await UserCRUD.get_with_expired_subscriptions(session)
    
    elif target_type == "channel" and target_filter:
        channel_id = target_filter.get("channel_id")
        return await UserCRUD.get_by_channel(session, channel_id)
    
    elif target_type == "new_users":
        days = target_filter.get("days", 7) if target_filter else 7
        return await UserCRUD.get_new(session, days=days)
    
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЗАДАЧА 4: ЕЖЕДНЕВНАЯ СТАТИСТИКА
# ═══════════════════════════════════════════════════════════════════════════════

async def generate_daily_stats() -> None:
    """Генерация ежедневной статистики."""
    logger.info("📊 Генерация ежедневной статистики...")
    
    try:
        async with async_session() as session:
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            
            # Собираем статистику за вчера
            stats = {
                "date": yesterday.isoformat(),
                "new_users": await UserCRUD.count_new_by_date(session, yesterday),
                "total_users": await UserCRUD.count_all(session),
                "new_subscriptions": await SubscriptionCRUD.count_new_by_date(session, yesterday),
                "active_subscriptions": await SubscriptionCRUD.count_active(session),
                "expired_subscriptions": await SubscriptionCRUD.count_expired_by_date(session, yesterday),
                "payments_count": await PaymentCRUD.count_by_date(session, yesterday),
                "payments_sum": await PaymentCRUD.sum_by_date(session, yesterday),
            }
            
            # Сохраняем в базу
            await StatsCRUD.save_daily(session, stats)
            await session.commit()
            
            logger.info(f"✅ Статистика за {yesterday} сохранена")
            
    except Exception as e:
        logger.exception(f"❌ Ошибка в generate_daily_stats: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЗАДАЧА 5: ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ
# ═══════════════════════════════════════════════════════════════════════════════

async def send_weekly_report() -> None:
    """Отправка еженедельного отчёта админам."""
    global _bot
    if not _bot:
        return
    
    logger.info("📊 Формирование еженедельного отчёта...")
    
    try:
        async with async_session() as session:
            # Период: последние 7 дней
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=7)
            
            # Собираем данные
            new_users = await UserCRUD.count_new_in_period(session, start_date, end_date)
            total_users = await UserCRUD.count_all(session)
            
            new_subscriptions = await SubscriptionCRUD.count_new_in_period(session, start_date, end_date)
            active_subscriptions = await SubscriptionCRUD.count_active(session)
            
            payments_count = await PaymentCRUD.count_in_period(session, start_date, end_date)
            payments_sum = await PaymentCRUD.sum_in_period(session, start_date, end_date)
            
            # Топ каналов по подпискам
            top_channels = await ChannelCRUD.get_top_by_subscriptions(session, limit=5)
            top_channels_text = ""
            for i, channel in enumerate(top_channels, 1):
                top_channels_text += f"  {i}. {channel.title}: {channel.subscriptions_count}\n"
            
            # Формируем отчёт
            report = (
                f"📊 <b>Еженедельный отчёт</b>\n"
                f"📅 {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}\n\n"
                
                f"👥 <b>Пользователи:</b>\n"
                f"  • Новых: <b>{new_users}</b>\n"
                f"  • Всего: <b>{total_users}</b>\n\n"
                
                f"📢 <b>Подписки:</b>\n"
                f"  • Новых: <b>{new_subscriptions}</b>\n"
                f"  • Активных: <b>{active_subscriptions}</b>\n\n"
                
                f"💰 <b>Платежи:</b>\n"
                f"  • Количество: <b>{payments_count}</b>\n"
                f"  • Сумма: <b>${payments_sum:.2f}</b>\n\n"
                
                f"🏆 <b>Топ каналов:</b>\n{top_channels_text or '  Нет данных'}"
            )
            
            # Отправляем всем админам
            for admin_id in settings.ADMIN_IDS:
                try:
                    await _bot.send_message(
                        chat_id=admin_id,
                        text=report,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отправить отчёт админу {admin_id}: {e}")
            
            logger.info("✅ Еженедельный отчёт отправлен")
            
    except Exception as e:
        logger.exception(f"❌ Ошибка в send_weekly_report: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЗАДАЧА 6: ОЧИСТКА СТАРЫХ ДАННЫХ
# ═══════════════════════════════════════════════════════════════════════════════

async def cleanup_old_data() -> None:
    """Очистка старых данных."""
    logger.info("🧹 Очистка старых данных...")
    
    try:
        async with async_session() as session:
            # Удаляем старые завершённые рассылки (старше 30 дней)
            deleted_broadcasts = await BroadcastCRUD.delete_old(session, days=30)
            
            # Удаляем старые истёкшие подписки (старше 90 дней)
            deleted_subscriptions = await SubscriptionCRUD.delete_old_expired(session, days=90)
            
            # Удаляем неоплаченные платежи (старше 7 дней)
            deleted_payments = await PaymentCRUD.delete_unpaid_old(session, days=7)
            
            await session.commit()
            
            logger.info(
                f"✅ Очистка завершена: "
                f"рассылок: {deleted_broadcasts}, "
                f"подписок: {deleted_subscriptions}, "
                f"платежей: {deleted_payments}"
            )
            
    except Exception as e:
        logger.exception(f"❌ Ошибка в cleanup_old_data: {e}")
    
    # Очистка старых логов
    try:
        from pathlib import Path
        import os
        
        log_dir = Path("logs")
        if log_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=14)  # Храним 14 дней
            
            for log_file in log_dir.glob("*.log"):
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    logger.info(f"🗑️ Удалён старый лог: {log_file.name}")
                    
    except Exception as e:
        logger.warning(f"⚠️ Ошибка очистки логов: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЗАДАЧА 7: ПРОВЕРКА НЕОПЛАЧЕННЫХ ИНВОЙСОВ
# ═══════════════════════════════════════════════════════════════════════════════

async def check_pending_payments() -> None:
    """Проверка статуса неоплаченных инвойсов через Crypto Bot API."""
    logger.info("💳 Проверка неоплаченных инвойсов...")
    
    if not settings.CRYPTO_BOT_TOKEN:
        return
    
    try:
        from services.crypto_bot import CryptoBotAPI
        
        crypto_bot = CryptoBotAPI(settings.CRYPTO_BOT_TOKEN)
        
        async with async_session() as session:
            # Получаем все pending платежи не старше 24 часов
            pending_payments = await PaymentCRUD.get_pending(session, hours=24)
            
            for payment in pending_payments:
                try:
                    if not payment.invoice_id:
                        continue
                    
                    # Проверяем статус в Crypto Bot
                    invoice = await crypto_bot.get_invoices(
                        invoice_ids=[payment.invoice_id]
                    )
                    
                    if invoice and invoice[0].status == "paid":
                        # Платёж прошёл!
                        logger.info(f"💰 Обнаружен оплаченный инвойс: {payment.invoice_id}")
                        
                        # Активируем подписку
                        await PaymentCRUD.mark_paid(session, payment.id)
                        
                        # Создаём или продляем подписку
                        # (логика из payment handler)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка проверки инвойса {payment.invoice_id}: {e}")
            
            await session.commit()
            
    except Exception as e:
        logger.exception(f"❌ Ошибка в check_pending_payments: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ЗАДАЧА 8: БЭКАП БАЗЫ ДАННЫХ
# ═══════════════════════════════════════════════════════════════════════════════

async def backup_database() -> None:
    """Создание резервной копии базы данных."""
    logger.info("💾 Создание бэкапа базы данных...")
    
    try:
        import shutil
        from pathlib import Path
        
        # Пути
        db_path = Path(settings.DATABASE_PATH)
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        # Имя файла бэкапа
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = backup_dir / backup_filename
        
        # Копируем файл БД
        if db_path.exists():
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Бэкап создан: {backup_path}")
            
            # Удаляем старые бэкапы (оставляем 7 последних)
            backups = sorted(backup_dir.glob("backup_*.db"), reverse=True)
            for old_backup in backups[7:]:
                old_backup.unlink()
                logger.info(f"🗑️ Удалён старый бэкап: {old_backup.name}")
        else:
            logger.warning(f"⚠️ Файл БД не найден: {db_path}")
            
    except Exception as e:
        logger.exception(f"❌ Ошибка создания бэкапа: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

async def run_task_manually(task_name: str) -> str:
    """Ручной запуск задачи."""
    tasks = {
        "check_expired": check_expired_subscriptions,
        "notifications": send_expiration_notifications,
        "broadcasts": process_scheduled_broadcasts,
        "daily_stats": generate_daily_stats,
        "weekly_report": send_weekly_report,
        "cleanup": cleanup_old_data,
        "check_payments": check_pending_payments,
        "backup": backup_database,
    }
    
    if task_name not in tasks:
        return f"❌ Задача '{task_name}' не найдена"
    
    try:
        await tasks[task_name]()
        return f"✅ Задача '{task_name}' выполнена"
    except Exception as e:
        return f"❌ Ошибка выполнения '{task_name}': {e}"
