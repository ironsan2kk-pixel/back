"""
Административный модуль: Статистика
Чат 5.2 - Telegram бот продажи доступов к каналам

Функционал:
- Общая статистика бота
- Статистика по каналам
- Статистика по пакетам
- Финансовая статистика
- Статистика подписок
- Экспорт отчётов
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import csv
import io

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, 
    Message,
    BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from database.models import (
    User, Channel, SubscriptionPackage, UserSubscription,
    Payment, Promocode, PromocodeUsage
)
from database.crud import (
    UserCRUD, ChannelCRUD, PackageCRUD,
    SubscriptionCRUD, PaymentCRUD, PromoCRUD
)
from keyboards.admin_kb import (
    get_stats_menu_kb,
    get_stats_period_kb,
    get_stats_channels_kb,
    get_stats_packages_kb,
    get_stats_export_kb,
    get_back_to_stats_kb
)
from states.admin_states import StatsAdminState
from utils.i18n import get_text

router = Router()


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def get_date_range(period: str) -> tuple[datetime, datetime]:
    """
    Получение диапазона дат для периода.
    
    Args:
        period: today, week, month, quarter, year, all
        
    Returns:
        Tuple[start_date, end_date]
    """
    now = datetime.utcnow()
    end_date = now
    
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "quarter":
        start_date = now - timedelta(days=90)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:  # all
        start_date = datetime(2020, 1, 1)
    
    return start_date, end_date


async def format_currency(amount: Decimal) -> str:
    """Форматирование суммы в валюте."""
    return f"${amount:,.2f}"


async def calculate_growth(
    current: int | Decimal, 
    previous: int | Decimal
) -> str:
    """
    Расчёт процента роста.
    
    Args:
        current: Текущее значение
        previous: Предыдущее значение
        
    Returns:
        Строка с процентом роста
    """
    if previous == 0:
        if current > 0:
            return "+∞%"
        return "0%"
    
    growth = ((current - previous) / previous) * 100
    
    if growth > 0:
        return f"+{growth:.1f}%"
    elif growth < 0:
        return f"{growth:.1f}%"
    return "0%"


# ==================== ГЛАВНОЕ МЕНЮ СТАТИСТИКИ ====================

@router.callback_query(F.data == "admin:stats")
async def show_stats_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Главное меню статистики.
    Показывает краткую сводку и навигацию.
    """
    await state.clear()
    lang = callback.from_user.language_code or "ru"
    
    # Получаем базовую статистику
    user_crud = UserCRUD(session)
    payment_crud = PaymentCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    
    # Всего пользователей
    total_users = await user_crud.count_all()
    
    # Новые пользователи за сегодня
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_today = await user_crud.count_by_date_range(today_start, datetime.utcnow())
    
    # Активные подписки
    active_subs = await subscription_crud.count_active()
    
    # Доход за сегодня
    today_revenue = await payment_crud.get_revenue_by_period(today_start, datetime.utcnow())
    
    # Доход за месяц
    month_start = datetime.utcnow() - timedelta(days=30)
    month_revenue = await payment_crud.get_revenue_by_period(month_start, datetime.utcnow())
    
    # Всего платежей
    total_payments = await payment_crud.count_completed()
    
    text = get_text("admin_stats_overview", lang).format(
        total_users=total_users,
        new_users_today=new_users_today,
        active_subs=active_subs,
        today_revenue=await format_currency(today_revenue or Decimal("0")),
        month_revenue=await format_currency(month_revenue or Decimal("0")),
        total_payments=total_payments
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_stats_menu_kb(lang)
    )
    await callback.answer()


# ==================== ОБЩАЯ СТАТИСТИКА ====================

@router.callback_query(F.data == "admin:stats:general")
async def show_general_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Выбор периода для общей статистики.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(StatsAdminState.selecting_period)
    await state.update_data(stats_type="general")
    
    text = get_text("admin_stats_select_period", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_stats_period_kb(lang)
    )
    await callback.answer()


@router.callback_query(
    StatsAdminState.selecting_period,
    F.data.startswith("admin:stats:period:")
)
async def show_general_stats_by_period(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Отображение общей статистики за выбранный период.
    """
    lang = callback.from_user.language_code or "ru"
    period = callback.data.split(":")[-1]
    
    data = await state.get_data()
    stats_type = data.get("stats_type", "general")
    
    start_date, end_date = await get_date_range(period)
    
    # Получаем статистику
    user_crud = UserCRUD(session)
    payment_crud = PaymentCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    promo_crud = PromoCRUD(session)
    
    # Пользователи
    new_users = await user_crud.count_by_date_range(start_date, end_date)
    total_users = await user_crud.count_all()
    
    # Подписки
    new_subscriptions = await subscription_crud.count_by_date_range(start_date, end_date)
    active_subscriptions = await subscription_crud.count_active()
    expired_subscriptions = await subscription_crud.count_expired_in_range(start_date, end_date)
    
    # Платежи
    total_revenue = await payment_crud.get_revenue_by_period(start_date, end_date)
    payments_count = await payment_crud.count_by_period(start_date, end_date)
    avg_payment = (total_revenue / payments_count) if payments_count > 0 else Decimal("0")
    
    # Промокоды
    promo_usages = await promo_crud.count_usages_by_period(start_date, end_date)
    promo_discount_total = await promo_crud.get_total_discount_by_period(start_date, end_date)
    
    # Для сравнения: предыдущий аналогичный период
    period_duration = end_date - start_date
    prev_end = start_date
    prev_start = prev_end - period_duration
    
    prev_new_users = await user_crud.count_by_date_range(prev_start, prev_end)
    prev_revenue = await payment_crud.get_revenue_by_period(prev_start, prev_end)
    prev_new_subs = await subscription_crud.count_by_date_range(prev_start, prev_end)
    
    # Форматирование периода
    period_names = {
        "today": get_text("period_today", lang),
        "week": get_text("period_week", lang),
        "month": get_text("period_month", lang),
        "quarter": get_text("period_quarter", lang),
        "year": get_text("period_year", lang),
        "all": get_text("period_all", lang)
    }
    
    text = get_text("admin_stats_general_detail", lang).format(
        period_name=period_names.get(period, period),
        start_date=start_date.strftime("%d.%m.%Y"),
        end_date=end_date.strftime("%d.%m.%Y"),
        # Пользователи
        new_users=new_users,
        users_growth=await calculate_growth(new_users, prev_new_users),
        total_users=total_users,
        # Подписки
        new_subscriptions=new_subscriptions,
        subs_growth=await calculate_growth(new_subscriptions, prev_new_subs),
        active_subscriptions=active_subscriptions,
        expired_subscriptions=expired_subscriptions,
        # Платежи
        total_revenue=await format_currency(total_revenue or Decimal("0")),
        revenue_growth=await calculate_growth(total_revenue or Decimal("0"), prev_revenue or Decimal("0")),
        payments_count=payments_count,
        avg_payment=await format_currency(avg_payment),
        # Промокоды
        promo_usages=promo_usages,
        promo_discount=await format_currency(promo_discount_total or Decimal("0"))
    )
    
    await state.update_data(current_period=period)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_stats_kb(lang)
    )
    await callback.answer()


# ==================== СТАТИСТИКА КАНАЛОВ ====================

@router.callback_query(F.data == "admin:stats:channels")
async def show_channels_stats_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Список каналов для просмотра статистики.
    """
    lang = callback.from_user.language_code or "ru"
    
    channel_crud = ChannelCRUD(session)
    channels = await channel_crud.get_all_active()
    
    if not channels:
        await callback.answer(
            get_text("admin_stats_no_channels", lang),
            show_alert=True
        )
        return
    
    await state.set_state(StatsAdminState.viewing_channel_stats)
    
    text = get_text("admin_stats_select_channel", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_stats_channels_kb(channels, lang)
    )
    await callback.answer()


@router.callback_query(
    StatsAdminState.viewing_channel_stats,
    F.data.startswith("admin:stats:channel:")
)
async def show_channel_stats_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Детальная статистика канала.
    """
    lang = callback.from_user.language_code or "ru"
    channel_id = int(callback.data.split(":")[-1])
    
    channel_crud = ChannelCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    payment_crud = PaymentCRUD(session)
    
    channel = await channel_crud.get_by_id(channel_id)
    if not channel:
        await callback.answer(
            get_text("admin_channel_not_found", lang),
            show_alert=True
        )
        return
    
    # Статистика за разные периоды
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    # Подписки
    active_subs = await subscription_crud.count_active_by_channel(channel_id)
    total_subs = await subscription_crud.count_by_channel(channel_id)
    
    subs_today = await subscription_crud.count_by_channel_and_period(
        channel_id, today_start, now
    )
    subs_week = await subscription_crud.count_by_channel_and_period(
        channel_id, week_start, now
    )
    subs_month = await subscription_crud.count_by_channel_and_period(
        channel_id, month_start, now
    )
    
    # Доход
    revenue_today = await payment_crud.get_channel_revenue_by_period(
        channel_id, today_start, now
    )
    revenue_week = await payment_crud.get_channel_revenue_by_period(
        channel_id, week_start, now
    )
    revenue_month = await payment_crud.get_channel_revenue_by_period(
        channel_id, month_start, now
    )
    revenue_total = await payment_crud.get_channel_total_revenue(channel_id)
    
    # Продления
    renewals_count = await subscription_crud.count_renewals_by_channel(channel_id)
    renewal_rate = (renewals_count / total_subs * 100) if total_subs > 0 else 0
    
    # Churn rate (отписки за месяц)
    churned_month = await subscription_crud.count_churned_by_channel_and_period(
        channel_id, month_start, now
    )
    churn_rate = (churned_month / active_subs * 100) if active_subs > 0 else 0
    
    # Средняя длительность подписки
    avg_duration = await subscription_crud.get_avg_duration_by_channel(channel_id)
    
    text = get_text("admin_stats_channel_detail", lang).format(
        channel_name=channel.name,
        channel_id=channel.telegram_id,
        # Подписки
        active_subs=active_subs,
        total_subs=total_subs,
        subs_today=subs_today,
        subs_week=subs_week,
        subs_month=subs_month,
        # Доход
        revenue_today=await format_currency(revenue_today or Decimal("0")),
        revenue_week=await format_currency(revenue_week or Decimal("0")),
        revenue_month=await format_currency(revenue_month or Decimal("0")),
        revenue_total=await format_currency(revenue_total or Decimal("0")),
        # Метрики
        renewal_rate=f"{renewal_rate:.1f}%",
        churn_rate=f"{churn_rate:.1f}%",
        avg_duration=f"{avg_duration:.0f}" if avg_duration else "—"
    )
    
    await state.update_data(selected_channel_id=channel_id)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_stats_kb(lang, back_to="admin:stats:channels")
    )
    await callback.answer()


# ==================== СТАТИСТИКА ПАКЕТОВ ====================

@router.callback_query(F.data == "admin:stats:packages")
async def show_packages_stats_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Список пакетов для просмотра статистики.
    """
    lang = callback.from_user.language_code or "ru"
    
    package_crud = PackageCRUD(session)
    packages = await package_crud.get_all_active()
    
    if not packages:
        await callback.answer(
            get_text("admin_stats_no_packages", lang),
            show_alert=True
        )
        return
    
    await state.set_state(StatsAdminState.viewing_package_stats)
    
    text = get_text("admin_stats_select_package", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_stats_packages_kb(packages, lang)
    )
    await callback.answer()


@router.callback_query(
    StatsAdminState.viewing_package_stats,
    F.data.startswith("admin:stats:package:")
)
async def show_package_stats_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Детальная статистика пакета.
    """
    lang = callback.from_user.language_code or "ru"
    package_id = int(callback.data.split(":")[-1])
    
    package_crud = PackageCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    payment_crud = PaymentCRUD(session)
    
    package = await package_crud.get_by_id(package_id)
    if not package:
        await callback.answer(
            get_text("admin_package_not_found", lang),
            show_alert=True
        )
        return
    
    # Статистика за разные периоды
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    # Подписки
    active_subs = await subscription_crud.count_active_by_package(package_id)
    total_subs = await subscription_crud.count_by_package(package_id)
    
    subs_today = await subscription_crud.count_by_package_and_period(
        package_id, today_start, now
    )
    subs_week = await subscription_crud.count_by_package_and_period(
        package_id, week_start, now
    )
    subs_month = await subscription_crud.count_by_package_and_period(
        package_id, month_start, now
    )
    
    # Доход
    revenue_today = await payment_crud.get_package_revenue_by_period(
        package_id, today_start, now
    )
    revenue_week = await payment_crud.get_package_revenue_by_period(
        package_id, week_start, now
    )
    revenue_month = await payment_crud.get_package_revenue_by_period(
        package_id, month_start, now
    )
    revenue_total = await payment_crud.get_package_total_revenue(package_id)
    
    # Популярность тарифа
    tier_30 = await subscription_crud.count_by_package_and_tier(package_id, 30)
    tier_90 = await subscription_crud.count_by_package_and_tier(package_id, 90)
    tier_365 = await subscription_crud.count_by_package_and_tier(package_id, 365)
    
    # Процентное распределение
    total_tier = tier_30 + tier_90 + tier_365
    if total_tier > 0:
        tier_30_pct = tier_30 / total_tier * 100
        tier_90_pct = tier_90 / total_tier * 100
        tier_365_pct = tier_365 / total_tier * 100
    else:
        tier_30_pct = tier_90_pct = tier_365_pct = 0
    
    # Список каналов в пакете
    channels = await package_crud.get_channels(package_id)
    channels_list = ", ".join([ch.name for ch in channels]) if channels else "—"
    
    text = get_text("admin_stats_package_detail", lang).format(
        package_name=package.name,
        channels_count=len(channels) if channels else 0,
        channels_list=channels_list,
        # Подписки
        active_subs=active_subs,
        total_subs=total_subs,
        subs_today=subs_today,
        subs_week=subs_week,
        subs_month=subs_month,
        # Доход
        revenue_today=await format_currency(revenue_today or Decimal("0")),
        revenue_week=await format_currency(revenue_week or Decimal("0")),
        revenue_month=await format_currency(revenue_month or Decimal("0")),
        revenue_total=await format_currency(revenue_total or Decimal("0")),
        # Распределение по тарифам
        tier_30=tier_30,
        tier_30_pct=f"{tier_30_pct:.1f}%",
        tier_90=tier_90,
        tier_90_pct=f"{tier_90_pct:.1f}%",
        tier_365=tier_365,
        tier_365_pct=f"{tier_365_pct:.1f}%"
    )
    
    await state.update_data(selected_package_id=package_id)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_stats_kb(lang, back_to="admin:stats:packages")
    )
    await callback.answer()


# ==================== ФИНАНСОВАЯ СТАТИСТИКА ====================

@router.callback_query(F.data == "admin:stats:finance")
async def show_finance_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Финансовая статистика.
    """
    lang = callback.from_user.language_code or "ru"
    
    payment_crud = PaymentCRUD(session)
    promo_crud = PromoCRUD(session)
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    quarter_start = now - timedelta(days=90)
    year_start = now - timedelta(days=365)
    
    # Доход по периодам
    revenue_today = await payment_crud.get_revenue_by_period(today_start, now)
    revenue_week = await payment_crud.get_revenue_by_period(week_start, now)
    revenue_month = await payment_crud.get_revenue_by_period(month_start, now)
    revenue_quarter = await payment_crud.get_revenue_by_period(quarter_start, now)
    revenue_year = await payment_crud.get_revenue_by_period(year_start, now)
    revenue_total = await payment_crud.get_total_revenue()
    
    # Количество платежей
    payments_today = await payment_crud.count_by_period(today_start, now)
    payments_week = await payment_crud.count_by_period(week_start, now)
    payments_month = await payment_crud.count_by_period(month_start, now)
    
    # Средний чек
    avg_today = (revenue_today / payments_today) if payments_today > 0 else Decimal("0")
    avg_week = (revenue_week / payments_week) if payments_week > 0 else Decimal("0")
    avg_month = (revenue_month / payments_month) if payments_month > 0 else Decimal("0")
    
    # Скидки от промокодов
    discount_today = await promo_crud.get_total_discount_by_period(today_start, now)
    discount_week = await promo_crud.get_total_discount_by_period(week_start, now)
    discount_month = await promo_crud.get_total_discount_by_period(month_start, now)
    discount_total = await promo_crud.get_total_discount()
    
    # Топ способов оплаты
    payment_methods = await payment_crud.get_payment_methods_stats()
    
    # Конверсия (платежи / пользователи)
    from database.crud import UserCRUD
    user_crud = UserCRUD(session)
    total_users = await user_crud.count_all()
    paying_users = await payment_crud.count_unique_payers()
    conversion = (paying_users / total_users * 100) if total_users > 0 else 0
    
    # LTV (средний доход на пользователя)
    ltv = (revenue_total / paying_users) if paying_users > 0 else Decimal("0")
    
    text = get_text("admin_stats_finance_detail", lang).format(
        # Доход
        revenue_today=await format_currency(revenue_today or Decimal("0")),
        revenue_week=await format_currency(revenue_week or Decimal("0")),
        revenue_month=await format_currency(revenue_month or Decimal("0")),
        revenue_quarter=await format_currency(revenue_quarter or Decimal("0")),
        revenue_year=await format_currency(revenue_year or Decimal("0")),
        revenue_total=await format_currency(revenue_total or Decimal("0")),
        # Платежи
        payments_today=payments_today,
        payments_week=payments_week,
        payments_month=payments_month,
        # Средний чек
        avg_today=await format_currency(avg_today),
        avg_week=await format_currency(avg_week),
        avg_month=await format_currency(avg_month),
        # Скидки
        discount_today=await format_currency(discount_today or Decimal("0")),
        discount_week=await format_currency(discount_week or Decimal("0")),
        discount_month=await format_currency(discount_month or Decimal("0")),
        discount_total=await format_currency(discount_total or Decimal("0")),
        # Метрики
        conversion=f"{conversion:.2f}%",
        paying_users=paying_users,
        ltv=await format_currency(ltv)
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_stats_kb(lang)
    )
    await callback.answer()


# ==================== ЭКСПОРТ СТАТИСТИКИ ====================

@router.callback_query(F.data == "admin:stats:export")
async def show_export_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Меню экспорта статистики.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(StatsAdminState.selecting_export)
    
    text = get_text("admin_stats_export_menu", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_stats_export_kb(lang)
    )
    await callback.answer()


@router.callback_query(
    StatsAdminState.selecting_export,
    F.data == "admin:stats:export:users"
)
async def export_users_csv(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Экспорт списка пользователей в CSV.
    """
    lang = callback.from_user.language_code or "ru"
    
    await callback.answer(get_text("admin_export_generating", lang))
    
    user_crud = UserCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    payment_crud = PaymentCRUD(session)
    
    users = await user_crud.get_all()
    
    # Создаём CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        "ID", "Telegram ID", "Username", "Full Name",
        "Language", "Is Banned", "Created At",
        "Active Subscriptions", "Total Payments", "Total Spent"
    ])
    
    # Данные
    for user in users:
        active_subs = await subscription_crud.count_active_by_user(user.id)
        total_payments = await payment_crud.count_by_user(user.id)
        total_spent = await payment_crud.get_user_total_spent(user.id)
        
        writer.writerow([
            user.id,
            user.telegram_id,
            user.username or "",
            user.full_name or "",
            user.language_code or "ru",
            "Yes" if user.is_banned else "No",
            user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            active_subs,
            total_payments,
            f"${total_spent:.2f}" if total_spent else "$0.00"
        ])
    
    # Отправляем файл
    output.seek(0)
    file_bytes = output.getvalue().encode('utf-8-sig')
    
    filename = f"users_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    await callback.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption=get_text("admin_export_users_caption", lang).format(
            count=len(users)
        )
    )
    
    await state.clear()


@router.callback_query(
    StatsAdminState.selecting_export,
    F.data == "admin:stats:export:payments"
)
async def export_payments_csv(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Экспорт платежей в CSV.
    """
    lang = callback.from_user.language_code or "ru"
    
    await callback.answer(get_text("admin_export_generating", lang))
    
    payment_crud = PaymentCRUD(session)
    
    payments = await payment_crud.get_all_completed()
    
    # Создаём CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        "ID", "User ID", "Amount", "Currency",
        "Status", "Payment Method", "Invoice ID",
        "Channel/Package", "Duration", "Created At", "Completed At"
    ])
    
    # Данные
    for payment in payments:
        target = ""
        if payment.channel_id:
            target = f"Channel #{payment.channel_id}"
        elif payment.package_id:
            target = f"Package #{payment.package_id}"
        
        writer.writerow([
            payment.id,
            payment.user_id,
            f"${payment.amount:.2f}",
            payment.currency or "USDT",
            payment.status,
            payment.payment_method or "crypto_bot",
            payment.invoice_id or "",
            target,
            f"{payment.duration_days} days" if payment.duration_days else "",
            payment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            payment.completed_at.strftime("%Y-%m-%d %H:%M:%S") if payment.completed_at else ""
        ])
    
    # Отправляем файл
    output.seek(0)
    file_bytes = output.getvalue().encode('utf-8-sig')
    
    filename = f"payments_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    total_amount = sum(p.amount for p in payments if p.amount)
    
    await callback.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption=get_text("admin_export_payments_caption", lang).format(
            count=len(payments),
            total=f"${total_amount:.2f}"
        )
    )
    
    await state.clear()


@router.callback_query(
    StatsAdminState.selecting_export,
    F.data == "admin:stats:export:subscriptions"
)
async def export_subscriptions_csv(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Экспорт подписок в CSV.
    """
    lang = callback.from_user.language_code or "ru"
    
    await callback.answer(get_text("admin_export_generating", lang))
    
    subscription_crud = SubscriptionCRUD(session)
    
    subscriptions = await subscription_crud.get_all()
    
    # Создаём CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        "ID", "User ID", "Channel ID", "Package ID",
        "Is Active", "Start Date", "End Date",
        "Days Remaining", "Is Renewal", "Created At"
    ])
    
    now = datetime.utcnow()
    
    # Данные
    for sub in subscriptions:
        days_remaining = (sub.end_date - now).days if sub.end_date > now else 0
        
        writer.writerow([
            sub.id,
            sub.user_id,
            sub.channel_id or "",
            sub.package_id or "",
            "Yes" if sub.is_active else "No",
            sub.start_date.strftime("%Y-%m-%d"),
            sub.end_date.strftime("%Y-%m-%d"),
            days_remaining if sub.is_active else 0,
            "Yes" if sub.is_renewal else "No",
            sub.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    # Отправляем файл
    output.seek(0)
    file_bytes = output.getvalue().encode('utf-8-sig')
    
    filename = f"subscriptions_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    active_count = sum(1 for s in subscriptions if s.is_active)
    
    await callback.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption=get_text("admin_export_subscriptions_caption", lang).format(
            count=len(subscriptions),
            active=active_count
        )
    )
    
    await state.clear()


@router.callback_query(
    StatsAdminState.selecting_export,
    F.data == "admin:stats:export:promos"
)
async def export_promos_csv(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Экспорт промокодов в CSV.
    """
    lang = callback.from_user.language_code or "ru"
    
    await callback.answer(get_text("admin_export_generating", lang))
    
    promo_crud = PromoCRUD(session)
    
    promos = await promo_crud.get_all()
    
    # Создаём CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        "ID", "Code", "Discount Type", "Discount Value",
        "Target", "Usage Limit", "Times Used",
        "Is Active", "Expires At", "Created At"
    ])
    
    # Данные
    for promo in promos:
        target = "All"
        if promo.channel_id:
            target = f"Channel #{promo.channel_id}"
        elif promo.package_id:
            target = f"Package #{promo.package_id}"
        
        writer.writerow([
            promo.id,
            promo.code,
            promo.discount_type,
            promo.discount_value,
            target,
            promo.usage_limit or "Unlimited",
            promo.times_used,
            "Yes" if promo.is_active else "No",
            promo.expires_at.strftime("%Y-%m-%d") if promo.expires_at else "Never",
            promo.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    # Отправляем файл
    output.seek(0)
    file_bytes = output.getvalue().encode('utf-8-sig')
    
    filename = f"promos_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    active_count = sum(1 for p in promos if p.is_active)
    total_used = sum(p.times_used for p in promos)
    
    await callback.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption=get_text("admin_export_promos_caption", lang).format(
            count=len(promos),
            active=active_count,
            total_used=total_used
        )
    )
    
    await state.clear()


@router.callback_query(
    StatsAdminState.selecting_export,
    F.data == "admin:stats:export:full_report"
)
async def export_full_report(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Экспорт полного отчёта.
    """
    lang = callback.from_user.language_code or "ru"
    
    await callback.answer(get_text("admin_export_generating", lang))
    
    user_crud = UserCRUD(session)
    payment_crud = PaymentCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    channel_crud = ChannelCRUD(session)
    package_crud = PackageCRUD(session)
    promo_crud = PromoCRUD(session)
    
    now = datetime.utcnow()
    month_start = now - timedelta(days=30)
    
    # Сбор данных
    report_data = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "users": {
            "total": await user_crud.count_all(),
            "new_this_month": await user_crud.count_by_date_range(month_start, now),
            "banned": await user_crud.count_banned()
        },
        "subscriptions": {
            "active": await subscription_crud.count_active(),
            "total": await subscription_crud.count_all(),
            "new_this_month": await subscription_crud.count_by_date_range(month_start, now)
        },
        "payments": {
            "total_revenue": float(await payment_crud.get_total_revenue() or 0),
            "month_revenue": float(await payment_crud.get_revenue_by_period(month_start, now) or 0),
            "total_count": await payment_crud.count_completed(),
            "month_count": await payment_crud.count_by_period(month_start, now)
        },
        "channels": {
            "total": await channel_crud.count_all(),
            "active": await channel_crud.count_active()
        },
        "packages": {
            "total": await package_crud.count_all(),
            "active": await package_crud.count_active()
        },
        "promos": {
            "total": await promo_crud.count_all(),
            "active": await promo_crud.count_active(),
            "total_used": await promo_crud.count_total_usages()
        }
    }
    
    # Формируем текстовый отчёт
    report_text = f"""
========================================
         FULL STATISTICS REPORT
========================================
Generated: {report_data['generated_at']}

--- USERS ---
Total Users: {report_data['users']['total']}
New This Month: {report_data['users']['new_this_month']}
Banned: {report_data['users']['banned']}

--- SUBSCRIPTIONS ---
Active: {report_data['subscriptions']['active']}
Total: {report_data['subscriptions']['total']}
New This Month: {report_data['subscriptions']['new_this_month']}

--- PAYMENTS ---
Total Revenue: ${report_data['payments']['total_revenue']:.2f}
Month Revenue: ${report_data['payments']['month_revenue']:.2f}
Total Payments: {report_data['payments']['total_count']}
Month Payments: {report_data['payments']['month_count']}

--- CHANNELS ---
Total: {report_data['channels']['total']}
Active: {report_data['channels']['active']}

--- PACKAGES ---
Total: {report_data['packages']['total']}
Active: {report_data['packages']['active']}

--- PROMO CODES ---
Total: {report_data['promos']['total']}
Active: {report_data['promos']['active']}
Total Used: {report_data['promos']['total_used']}

========================================
"""
    
    file_bytes = report_text.encode('utf-8')
    filename = f"full_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    
    await callback.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption=get_text("admin_export_full_report_caption", lang)
    )
    
    await state.clear()


# ==================== НАВИГАЦИЯ ====================

@router.callback_query(F.data == "admin:stats:back")
async def back_to_stats_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Возврат в главное меню статистики.
    """
    await show_stats_menu(callback, session, state)


def setup_stats_handlers(dp):
    """Регистрация хэндлеров статистики."""
    dp.include_router(router)
