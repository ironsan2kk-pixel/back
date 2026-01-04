"""
═══════════════════════════════════════════════════════════════════════════════
🏠 ГЛАВНОЕ МЕНЮ АДМИН-ПАНЕЛИ
═══════════════════════════════════════════════════════════════════════════════
Точка входа в админку и главное меню.

Функционал:
- Команда /admin для входа в админку
- Проверка прав администратора
- Главное меню с навигацией
- Быстрая статистика на главном экране
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional
import logging

from database.crud import (
    UserCRUD,
    ChannelCRUD,
    PackageCRUD,
    SubscriptionCRUD,
    PaymentCRUD,
    PromoCRUD,
)
from keyboards.admin_kb import (
    get_admin_main_menu,
    get_channels_menu,
    get_packages_menu,
    get_pricing_menu,
    get_promos_menu,
    get_users_menu,
    get_stats_menu,
    get_broadcast_menu,
    get_settings_menu,
)
from config import settings

logger = logging.getLogger(__name__)

router = Router(name="admin_main")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔐 ФИЛЬТР АДМИНИСТРАТОРА
# ═══════════════════════════════════════════════════════════════════════════════

class AdminFilter:
    """
    Фильтр проверки прав администратора.
    
    Проверяет:
    1. ID в списке ADMIN_IDS из конфига
    2. Роль пользователя в БД (is_admin)
    """
    
    async def __call__(self, event: Message | CallbackQuery, session: AsyncSession) -> bool:
        user_id = event.from_user.id
        
        # Проверка в конфиге
        if user_id in settings.ADMIN_IDS:
            return True
        
        # Проверка в БД
        user = await UserCRUD.get_by_telegram_id(session, user_id)
        if user and user.is_admin:
            return True
        
        return False


def is_admin(user_id: int, session: Optional[AsyncSession] = None) -> bool:
    """Синхронная проверка админа (только по конфигу)."""
    return user_id in settings.ADMIN_IDS


async def check_admin(
    event: Message | CallbackQuery,
    session: AsyncSession
) -> bool:
    """Асинхронная проверка админа."""
    user_id = event.from_user.id
    
    if user_id in settings.ADMIN_IDS:
        return True
    
    user = await UserCRUD.get_by_telegram_id(session, user_id)
    return user and user.is_admin


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ФОРМИРОВАНИЕ СТАТИСТИКИ
# ═══════════════════════════════════════════════════════════════════════════════

async def get_quick_stats(session: AsyncSession) -> dict:
    """
    Получение быстрой статистики для главного меню.
    
    Returns:
        dict с ключами:
            - total_users: всего пользователей
            - active_subs: активных подписок
            - today_sales: продаж сегодня
            - today_revenue: доход сегодня (USDT)
            - pending_payments: ожидающих оплаты
    """
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Всего пользователей
    total_users = await UserCRUD.count_all(session)
    
    # Активные подписки
    active_subs = await SubscriptionCRUD.count_active(session)
    
    # Продажи сегодня
    today_payments = await PaymentCRUD.get_by_date_range(
        session,
        start_date=today_start,
        end_date=datetime.utcnow(),
        status="completed"
    )
    today_sales = len(today_payments)
    today_revenue = sum(p.amount_usdt for p in today_payments)
    
    # Ожидающие оплаты
    pending_payments = await PaymentCRUD.count_pending(session)
    
    return {
        "total_users": total_users,
        "active_subs": active_subs,
        "today_sales": today_sales,
        "today_revenue": float(today_revenue),
        "pending_payments": pending_payments,
    }


def format_admin_main_text(stats: dict) -> str:
    """Форматирование текста главного меню."""
    return f"""
🔐 <b>Админ-панель</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Быстрая статистика</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 Всего пользователей: <b>{stats['total_users']:,}</b>
✅ Активных подписок: <b>{stats['active_subs']:,}</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Сегодня</b>
━━━━━━━━━━━━━━━━━━━━━━

💰 Продаж: <b>{stats['today_sales']}</b>
💵 Доход: <b>${stats['today_revenue']:.2f}</b> USDT
⏳ Ожидают оплаты: <b>{stats['pending_payments']}</b>

━━━━━━━━━━━━━━━━━━━━━━
Выберите раздел:
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 🏠 КОМАНДА /ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Команда /admin — вход в админ-панель.
    
    Проверяет права и показывает главное меню.
    """
    # Сброс состояния
    await state.clear()
    
    # Проверка прав
    if not await check_admin(message, session):
        await message.answer(
            "⛔ У вас нет доступа к админ-панели.",
            parse_mode="HTML"
        )
        logger.warning(
            f"Unauthorized admin access attempt: user_id={message.from_user.id}, "
            f"username=@{message.from_user.username}"
        )
        return
    
    # Получение статистики
    try:
        stats = await get_quick_stats(session)
    except Exception as e:
        logger.error(f"Failed to get quick stats: {e}")
        stats = {
            "total_users": 0,
            "active_subs": 0,
            "today_sales": 0,
            "today_revenue": 0.0,
            "pending_payments": 0,
        }
    
    # Отправка меню
    await message.answer(
        format_admin_main_text(stats),
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML"
    )
    
    logger.info(f"Admin panel opened: user_id={message.from_user.id}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 CALLBACK: ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:main")
async def callback_admin_main(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Возврат в главное меню админки."""
    await state.clear()
    
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    try:
        stats = await get_quick_stats(session)
    except Exception as e:
        logger.error(f"Failed to get quick stats: {e}")
        stats = {
            "total_users": 0,
            "active_subs": 0,
            "today_sales": 0,
            "today_revenue": 0.0,
            "pending_payments": 0,
        }
    
    await callback.message.edit_text(
        format_admin_main_text(stats),
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:refresh")
async def callback_admin_refresh(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Обновление статистики на главном экране."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    try:
        stats = await get_quick_stats(session)
        await callback.message.edit_text(
            format_admin_main_text(stats),
            reply_markup=get_admin_main_menu(),
            parse_mode="HTML"
        )
        await callback.answer("✅ Обновлено")
    except Exception as e:
        logger.error(f"Failed to refresh stats: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 📂 НАВИГАЦИЯ ПО РАЗДЕЛАМ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:channels")
async def callback_channels_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Переход в раздел каналов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    # Получаем количество каналов
    channels = await ChannelCRUD.get_all(session)
    active_count = sum(1 for c in channels if c.is_active)
    
    text = f"""
📢 <b>Управление каналами</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 Всего каналов: <b>{len(channels)}</b>
✅ Активных: <b>{active_count}</b>
❌ Неактивных: <b>{len(channels) - active_count}</b>
━━━━━━━━━━━━━━━━━━━━━━

Выберите действие:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_channels_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:packages")
async def callback_packages_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Переход в раздел пакетов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    packages = await PackageCRUD.get_all(session)
    active_count = sum(1 for p in packages if p.is_active)
    
    text = f"""
📦 <b>Управление пакетами</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 Всего пакетов: <b>{len(packages)}</b>
✅ Активных: <b>{active_count}</b>
━━━━━━━━━━━━━━━━━━━━━━

Пакеты позволяют объединять несколько каналов
со скидкой для покупателей.

Выберите действие:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_packages_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:pricing")
async def callback_pricing_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Переход в раздел тарифов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    text = """
💰 <b>Управление тарифами</b>

━━━━━━━━━━━━━━━━━━━━━━
Тарифы определяют цены на подписки
для каждого канала и пакета.

📌 Каждый канал/пакет может иметь
несколько тарифов (7/30/90/365 дней).
━━━━━━━━━━━━━━━━━━━━━━

Выберите действие:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pricing_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:promos")
async def callback_promos_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Переход в раздел промокодов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    # Статистика промокодов
    promos = await PromoCRUD.get_all(session)
    active_count = sum(1 for p in promos if p.is_active)
    total_uses = sum(p.current_uses for p in promos)
    
    text = f"""
🎟️ <b>Управление промокодами</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 Всего промокодов: <b>{len(promos)}</b>
✅ Активных: <b>{active_count}</b>
🔢 Всего использований: <b>{total_uses}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Типы промокодов:</b>
• 💸 Скидка (% или фикс. сумма)
• 🆓 Бесплатный доступ
• ⏰ Бонусное время

Выберите действие:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promos_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:users")
async def callback_users_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Переход в раздел пользователей."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    # Статистика пользователей
    total_users = await UserCRUD.count_all(session)
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    new_today = await UserCRUD.count_by_date_range(session, today_start)
    blocked_count = await UserCRUD.count_blocked(session)
    
    text = f"""
👥 <b>Управление пользователями</b>

━━━━━━━━━━━━━━━━━━━━━━
📊 Всего: <b>{total_users:,}</b>
🆕 Новых сегодня: <b>{new_today}</b>
🚫 Заблокировано: <b>{blocked_count}</b>
━━━━━━━━━━━━━━━━━━━━━━

Выберите действие:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_users_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:stats")
async def callback_stats_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Переход в раздел статистики."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    text = """
📊 <b>Статистика</b>

━━━━━━━━━━━━━━━━━━━━━━
Детальная аналитика по всем
аспектам работы бота.
━━━━━━━━━━━━━━━━━━━━━━

Выберите раздел:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:broadcast")
async def callback_broadcast_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Переход в раздел рассылки."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    total_users = await UserCRUD.count_all(session)
    active_subs = await SubscriptionCRUD.count_active(session)
    
    text = f"""
📨 <b>Рассылка</b>

━━━━━━━━━━━━━━━━━━━━━━
👥 Всего пользователей: <b>{total_users:,}</b>
✅ С активной подпиской: <b>{active_subs:,}</b>
━━━━━━━━━━━━━━━━━━━━━━

⚠️ <i>Рассылка отправляется асинхронно.
Скорость: ~30 сообщений/сек</i>

Выберите действие:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_broadcast_menu(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:settings")
async def callback_settings_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Переход в раздел настроек."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    text = """
⚙️ <b>Настройки</b>

━━━━━━━━━━━━━━━━━━━━━━
Конфигурация бота и системы.
━━━━━━━━━━━━━━━━━━━━━━

Выберите раздел:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ОБРАБОТКА NOOP (пустых) CALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.endswith(":noop"))
async def callback_noop(callback: CallbackQuery):
    """Пустой обработчик для информационных кнопок."""
    await callback.answer()
