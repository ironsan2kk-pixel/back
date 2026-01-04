"""
═══════════════════════════════════════════════════════════════════════════════
👥 АДМИН-ПАНЕЛЬ — УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
═══════════════════════════════════════════════════════════════════════════════
Управление пользователями:
- Просмотр списка с фильтрацией и пагинацией
- Поиск по ID, username, имени
- Просмотр профиля и подписок
- Бан/разбан
- Ручная выдача/отзыв доступа
- Экспорт данных
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from keyboards.admin_kb import (
    get_users_menu_keyboard,
    get_users_list_keyboard,
    get_user_detail_keyboard,
    get_user_subscriptions_keyboard,
    get_user_grant_channels_keyboard,
    get_user_grant_packages_keyboard,
    get_user_grant_duration_keyboard,
    get_confirm_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
)
from states.admin_states import UserAdminState
from database.crud import (
    UserCRUD, 
    SubscriptionCRUD, 
    PaymentCRUD, 
    ChannelCRUD, 
    PackageCRUD
)
from services.channel_service import ChannelService
from utils.i18n import get_text

logger = logging.getLogger(__name__)
router = Router(name="admin_users")

ITEMS_PER_PAGE = 10


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def format_user_info(user: dict, detailed: bool = False) -> str:
    """Форматирование информации о пользователе."""
    # Основная информация
    username = f"@{user.get('username')}" if user.get('username') else "—"
    full_name = user.get('full_name', '—')
    
    # Статус
    if user.get('is_banned'):
        status = "🚫 Заблокирован"
    elif user.get('has_active_subscription'):
        status = "✅ Активен"
    else:
        status = "👤 Обычный"
    
    text = (
        f"👤 <b>{full_name}</b>\n"
        f"🆔 <code>{user.get('telegram_id')}</code>\n"
        f"📧 {username}\n"
        f"📊 Статус: {status}\n"
    )
    
    if detailed:
        # Дата регистрации
        if user.get('created_at'):
            reg_date = user['created_at'].strftime('%d.%m.%Y')
            text += f"📅 Регистрация: {reg_date}\n"
        
        # Язык
        lang = user.get('language_code', 'ru').upper()
        text += f"🌐 Язык: {lang}\n"
        
        # Количество подписок
        if user.get('subscriptions_count', 0) > 0:
            text += f"📦 Подписок: {user['subscriptions_count']}\n"
        
        # Всего платежей
        if user.get('total_payments', 0) > 0:
            text += f"💰 Платежей: ${user['total_payments']:.2f}\n"
    
    return text


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ГЛАВНОЕ МЕНЮ ПОЛЬЗОВАТЕЛЕЙ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:users")
async def show_users_menu(callback: CallbackQuery, state: FSMContext):
    """Главное меню управления пользователями."""
    await state.clear()
    
    # Статистика
    total_users = await UserCRUD.count_all()
    active_users = await UserCRUD.count_with_active_subscription()
    new_today = await UserCRUD.count_registered_today()
    new_week = await UserCRUD.count_registered_this_week()
    banned_users = await UserCRUD.count_banned()
    
    text = (
        "👥 <b>Управление пользователями</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ Всего: <b>{total_users:,}</b>\n"
        f"├ С активной подпиской: <b>{active_users:,}</b>\n"
        f"├ Новых сегодня: <b>{new_today}</b>\n"
        f"├ Новых за неделю: <b>{new_week}</b>\n"
        f"└ Заблокировано: <b>{banned_users}</b>\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_users_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:users:list"))
async def show_users_list(callback: CallbackQuery, state: FSMContext):
    """Список пользователей с фильтрацией."""
    parts = callback.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    filter_type = parts[4] if len(parts) > 4 else "all"
    
    # Получаем пользователей в зависимости от фильтра
    if filter_type == "active":
        users = await UserCRUD.get_with_active_subscription(
            offset=page * ITEMS_PER_PAGE, 
            limit=ITEMS_PER_PAGE
        )
        total = await UserCRUD.count_with_active_subscription()
        title = "✅ Пользователи с подпиской"
    elif filter_type == "banned":
        users = await UserCRUD.get_banned(
            offset=page * ITEMS_PER_PAGE, 
            limit=ITEMS_PER_PAGE
        )
        total = await UserCRUD.count_banned()
        title = "🚫 Заблокированные"
    elif filter_type == "new":
        users = await UserCRUD.get_registered_this_week(
            offset=page * ITEMS_PER_PAGE, 
            limit=ITEMS_PER_PAGE
        )
        total = await UserCRUD.count_registered_this_week()
        title = "🆕 Новые за неделю"
    else:
        users = await UserCRUD.get_all(
            offset=page * ITEMS_PER_PAGE, 
            limit=ITEMS_PER_PAGE
        )
        total = await UserCRUD.count_all()
        title = "📋 Все пользователи"
    
    if not users:
        text = f"{title}\n\n📭 Пользователи не найдены"
    else:
        text = f"{title}\n\n"
        for user in users:
            # Статус иконка
            if user.is_banned:
                icon = "🚫"
            elif await SubscriptionCRUD.has_active(user.telegram_id):
                icon = "✅"
            else:
                icon = "👤"
            
            username = f"@{user.username}" if user.username else ""
            name = user.full_name or "Без имени"
            
            text += f"{icon} <code>{user.telegram_id}</code> — {name} {username}\n"
    
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    text += f"\n📄 Страница {page + 1}/{max(1, total_pages)}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_users_list_keyboard(users, page, total_pages, filter_type),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 ПОИСК ПОЛЬЗОВАТЕЛЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:users:search")
async def start_user_search(callback: CallbackQuery, state: FSMContext):
    """Начало поиска пользователя."""
    await state.set_state(UserAdminState.searching)
    
    text = (
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Введите:\n"
        "• Telegram ID (число)\n"
        "• Username (без @)\n"
        "• Имя или фамилию"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard("admin:users"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(StateFilter(UserAdminState.searching))
async def process_user_search(message: Message, state: FSMContext):
    """Обработка поискового запроса."""
    query = message.text.strip()
    
    # Поиск по ID
    if query.isdigit():
        user = await UserCRUD.get_by_telegram_id(int(query))
        if user:
            await state.clear()
            await show_user_profile(message, user.id)
            return
    
    # Поиск по username
    if query.startswith("@"):
        query = query[1:]
    
    users = await UserCRUD.search(query, limit=10)
    
    if not users:
        await message.answer(
            "❌ Пользователи не найдены.\n"
            "Попробуйте другой запрос:",
            reply_markup=get_cancel_keyboard("admin:users")
        )
        return
    
    if len(users) == 1:
        await state.clear()
        await show_user_profile(message, users[0].id)
        return
    
    # Показываем список найденных
    text = f"🔍 <b>Найдено: {len(users)}</b>\n\n"
    for user in users:
        username = f"@{user.username}" if user.username else ""
        name = user.full_name or "Без имени"
        text += f"• <code>{user.telegram_id}</code> — {name} {username}\n"
    
    text += "\nВведите точный ID для просмотра профиля:"
    
    await message.answer(text, parse_mode="HTML")


async def show_user_profile(message: Message, user_id: int):
    """Показ профиля пользователя."""
    user = await UserCRUD.get_by_id(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден")
        return
    
    # Получаем дополнительные данные
    subscriptions = await SubscriptionCRUD.get_active_by_user(user.telegram_id)
    total_payments = await PaymentCRUD.get_total_by_user(user.telegram_id)
    
    text = format_user_info({
        'telegram_id': user.telegram_id,
        'username': user.username,
        'full_name': user.full_name,
        'is_banned': user.is_banned,
        'has_active_subscription': len(subscriptions) > 0,
        'created_at': user.created_at,
        'language_code': user.language_code,
        'subscriptions_count': len(subscriptions),
        'total_payments': total_payments,
    }, detailed=True)
    
    # Активные подписки
    if subscriptions:
        text += "\n📦 <b>Активные подписки:</b>\n"
        for sub in subscriptions:
            expires = sub.expires_at.strftime('%d.%m.%Y')
            if sub.channel_id:
                channel = await ChannelCRUD.get_by_id(sub.channel_id)
                name = channel.title if channel else f"Канал #{sub.channel_id}"
            elif sub.package_id:
                package = await PackageCRUD.get_by_id(sub.package_id)
                name = package.name if package else f"Пакет #{sub.package_id}"
            else:
                name = "—"
            text += f"├ {name} → {expires}\n"
    
    await message.answer(
        text,
        reply_markup=get_user_detail_keyboard(user.id, user.is_banned),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 ПРОСМОТР ПРОФИЛЯ (из списка)
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:user:view:"))
async def view_user_profile(callback: CallbackQuery, state: FSMContext):
    """Просмотр профиля пользователя из списка."""
    user_id = int(callback.data.split(":")[3])
    
    user = await UserCRUD.get_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Получаем дополнительные данные
    subscriptions = await SubscriptionCRUD.get_active_by_user(user.telegram_id)
    total_payments = await PaymentCRUD.get_total_by_user(user.telegram_id)
    
    text = format_user_info({
        'telegram_id': user.telegram_id,
        'username': user.username,
        'full_name': user.full_name,
        'is_banned': user.is_banned,
        'has_active_subscription': len(subscriptions) > 0,
        'created_at': user.created_at,
        'language_code': user.language_code,
        'subscriptions_count': len(subscriptions),
        'total_payments': total_payments,
    }, detailed=True)
    
    # Активные подписки
    if subscriptions:
        text += "\n📦 <b>Активные подписки:</b>\n"
        for sub in subscriptions:
            expires = sub.expires_at.strftime('%d.%m.%Y')
            if sub.channel_id:
                channel = await ChannelCRUD.get_by_id(sub.channel_id)
                name = channel.title if channel else f"Канал #{sub.channel_id}"
            elif sub.package_id:
                package = await PackageCRUD.get_by_id(sub.package_id)
                name = package.name if package else f"Пакет #{sub.package_id}"
            else:
                name = "—"
            text += f"├ {name} → {expires}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_user_detail_keyboard(user.id, user.is_banned),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ПОДПИСКИ ПОЛЬЗОВАТЕЛЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:user:subs:"))
async def show_user_subscriptions(callback: CallbackQuery, state: FSMContext):
    """Просмотр всех подписок пользователя."""
    user_id = int(callback.data.split(":")[3])
    
    user = await UserCRUD.get_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    # Все подписки (активные и истёкшие)
    subscriptions = await SubscriptionCRUD.get_all_by_user(user.telegram_id)
    
    text = f"📦 <b>Подписки пользователя</b>\n\n"
    text += f"👤 <code>{user.telegram_id}</code>\n\n"
    
    if not subscriptions:
        text += "📭 Нет подписок"
    else:
        active_subs = [s for s in subscriptions if s.is_active and s.expires_at > datetime.utcnow()]
        expired_subs = [s for s in subscriptions if not s.is_active or s.expires_at <= datetime.utcnow()]
        
        if active_subs:
            text += "✅ <b>Активные:</b>\n"
            for sub in active_subs:
                expires = sub.expires_at.strftime('%d.%m.%Y')
                if sub.channel_id:
                    channel = await ChannelCRUD.get_by_id(sub.channel_id)
                    name = channel.title if channel else f"#{sub.channel_id}"
                elif sub.package_id:
                    package = await PackageCRUD.get_by_id(sub.package_id)
                    name = package.name if package else f"#{sub.package_id}"
                else:
                    name = "—"
                text += f"├ {name} → {expires}\n"
            text += "\n"
        
        if expired_subs:
            text += "⏰ <b>Истёкшие:</b>\n"
            for sub in expired_subs[:5]:  # Показываем только 5 последних
                expires = sub.expires_at.strftime('%d.%m.%Y')
                if sub.channel_id:
                    channel = await ChannelCRUD.get_by_id(sub.channel_id)
                    name = channel.title if channel else f"#{sub.channel_id}"
                elif sub.package_id:
                    package = await PackageCRUD.get_by_id(sub.package_id)
                    name = package.name if package else f"#{sub.package_id}"
                else:
                    name = "—"
                text += f"├ {name} — истёк {expires}\n"
            
            if len(expired_subs) > 5:
                text += f"└ ... и ещё {len(expired_subs) - 5}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_user_subscriptions_keyboard(user_id, subscriptions),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# 🚫 БАН / РАЗБАН
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:user:ban:"))
async def confirm_ban_user(callback: CallbackQuery, state: FSMContext):
    """Подтверждение бана пользователя."""
    user_id = int(callback.data.split(":")[3])
    
    user = await UserCRUD.get_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    text = (
        f"🚫 <b>Блокировка пользователя</b>\n\n"
        f"👤 <code>{user.telegram_id}</code>\n"
        f"📧 @{user.username or '—'}\n\n"
        "⚠️ Пользователь будет:\n"
        "• Удалён из всех каналов\n"
        "• Не сможет пользоваться ботом\n\n"
        "Продолжить?"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_keyboard(
            f"admin:user:ban_confirm:{user_id}",
            f"admin:user:view:{user_id}"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:ban_confirm:"))
async def ban_user(callback: CallbackQuery, state: FSMContext):
    """Блокировка пользователя."""
    user_id = int(callback.data.split(":")[3])
    
    user = await UserCRUD.get_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    try:
        # Баним пользователя
        await UserCRUD.update(user.id, is_banned=True)
        
        # Деактивируем все подписки
        await SubscriptionCRUD.deactivate_all_by_user(user.telegram_id)
        
        # Кикаем из всех каналов
        subscriptions = await SubscriptionCRUD.get_all_by_user(user.telegram_id)
        for sub in subscriptions:
            if sub.channel_id:
                channel = await ChannelCRUD.get_by_id(sub.channel_id)
                if channel:
                    await ChannelService.kick_user(channel.telegram_id, user.telegram_id)
            elif sub.package_id:
                package = await PackageCRUD.get_by_id(sub.package_id)
                if package:
                    for channel_id in package.channel_ids:
                        channel = await ChannelCRUD.get_by_id(channel_id)
                        if channel:
                            await ChannelService.kick_user(channel.telegram_id, user.telegram_id)
        
        await callback.answer("✅ Пользователь заблокирован", show_alert=True)
        
        # Обновляем профиль
        await view_user_profile(callback, state)
        
    except Exception as e:
        logger.error(f"Error banning user {user_id}: {e}")
        await callback.answer("❌ Ошибка при блокировке", show_alert=True)


@router.callback_query(F.data.startswith("admin:user:unban:"))
async def unban_user(callback: CallbackQuery, state: FSMContext):
    """Разблокировка пользователя."""
    user_id = int(callback.data.split(":")[3])
    
    user = await UserCRUD.get_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    await UserCRUD.update(user.id, is_banned=False)
    
    await callback.answer("✅ Пользователь разблокирован", show_alert=True)
    
    # Обновляем профиль
    await view_user_profile(callback, state)


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ ВЫДАЧА ДОСТУПА — ШАГ 1: ВЫБОР ТИПА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:user:grant:"))
async def start_grant_access(callback: CallbackQuery, state: FSMContext):
    """Начало выдачи доступа пользователю."""
    user_id = int(callback.data.split(":")[3])
    
    user = await UserCRUD.get_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    if user.is_banned:
        await callback.answer("❌ Пользователь заблокирован", show_alert=True)
        return
    
    await state.update_data(grant_user_id=user_id, grant_telegram_id=user.telegram_id)
    await state.set_state(UserAdminState.grant_selecting_type)
    
    text = (
        f"➕ <b>Выдача доступа</b>\n\n"
        f"👤 <code>{user.telegram_id}</code>\n\n"
        "Выберите что выдать:"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Канал", callback_data="admin:grant:type:channel")],
        [InlineKeyboardButton(text="📦 Пакет", callback_data="admin:grant:type:package")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin:user:view:{user_id}")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ ВЫДАЧА ДОСТУПА — ШАГ 2: ВЫБОР КАНАЛА/ПАКЕТА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(
    StateFilter(UserAdminState.grant_selecting_type),
    F.data.startswith("admin:grant:type:")
)
async def select_grant_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа выдачи — канал или пакет."""
    grant_type = callback.data.split(":")[3]
    await state.update_data(grant_type=grant_type)
    
    if grant_type == "channel":
        channels = await ChannelCRUD.get_all_active()
        if not channels:
            await callback.answer("❌ Нет активных каналов", show_alert=True)
            return
        
        await state.set_state(UserAdminState.grant_selecting_item)
        
        text = "📢 <b>Выберите канал:</b>"
        await callback.message.edit_text(
            text,
            reply_markup=get_user_grant_channels_keyboard(channels),
            parse_mode="HTML"
        )
    
    else:  # package
        packages = await PackageCRUD.get_all_active()
        if not packages:
            await callback.answer("❌ Нет активных пакетов", show_alert=True)
            return
        
        await state.set_state(UserAdminState.grant_selecting_item)
        
        text = "📦 <b>Выберите пакет:</b>"
        await callback.message.edit_text(
            text,
            reply_markup=get_user_grant_packages_keyboard(packages),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(
    StateFilter(UserAdminState.grant_selecting_item),
    F.data.startswith("admin:grant:channel:")
)
async def select_grant_channel(callback: CallbackQuery, state: FSMContext):
    """Выбор канала для выдачи."""
    channel_id = int(callback.data.split(":")[3])
    await state.update_data(grant_channel_id=channel_id, grant_package_id=None)
    await proceed_to_duration_selection(callback, state)
    await callback.answer()


@router.callback_query(
    StateFilter(UserAdminState.grant_selecting_item),
    F.data.startswith("admin:grant:package:")
)
async def select_grant_package(callback: CallbackQuery, state: FSMContext):
    """Выбор пакета для выдачи."""
    package_id = int(callback.data.split(":")[3])
    await state.update_data(grant_package_id=package_id, grant_channel_id=None)
    await proceed_to_duration_selection(callback, state)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ ВЫДАЧА ДОСТУПА — ШАГ 3: ВЫБОР СРОКА
# ═══════════════════════════════════════════════════════════════════════════════

async def proceed_to_duration_selection(callback: CallbackQuery, state: FSMContext):
    """Переход к выбору срока доступа."""
    await state.set_state(UserAdminState.grant_selecting_duration)
    
    text = "📅 <b>Выберите срок доступа:</b>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_user_grant_duration_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(
    StateFilter(UserAdminState.grant_selecting_duration),
    F.data.startswith("admin:grant:days:")
)
async def select_grant_duration(callback: CallbackQuery, state: FSMContext):
    """Выбор срока выдачи."""
    days = int(callback.data.split(":")[3])
    
    if days == 0:
        # Кастомный срок
        await state.set_state(UserAdminState.grant_entering_custom_days)
        await callback.message.edit_text(
            "📅 <b>Введите количество дней:</b>",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await state.update_data(grant_days=days)
    await show_grant_confirmation(callback, state)
    await callback.answer()


@router.message(StateFilter(UserAdminState.grant_entering_custom_days))
async def process_custom_days(message: Message, state: FSMContext):
    """Обработка кастомного срока."""
    try:
        days = int(message.text.strip())
        if days < 1 or days > 3650:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 1 до 3650:")
        return
    
    await state.update_data(grant_days=days)
    
    # Создаём фейковый callback для показа подтверждения
    class FakeCallback:
        message = message
        def answer(self): pass
    
    await show_grant_confirmation(FakeCallback(), state)


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ ВЫДАЧА ДОСТУПА — ШАГ 4: ПОДТВЕРЖДЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

async def show_grant_confirmation(callback, state: FSMContext):
    """Показ подтверждения выдачи доступа."""
    await state.set_state(UserAdminState.grant_confirming)
    data = await state.get_data()
    
    user_id = data.get('grant_user_id')
    telegram_id = data.get('grant_telegram_id')
    days = data.get('grant_days')
    
    # Определяем что выдаём
    if data.get('grant_channel_id'):
        channel = await ChannelCRUD.get_by_id(data['grant_channel_id'])
        item_name = f"📢 {channel.title}" if channel else "—"
    else:
        package = await PackageCRUD.get_by_id(data['grant_package_id'])
        item_name = f"📦 {package.name}" if package else "—"
    
    expires_at = datetime.utcnow() + timedelta(days=days)
    
    text = (
        "✅ <b>Подтверждение выдачи доступа</b>\n\n"
        f"👤 User ID: <code>{telegram_id}</code>\n"
        f"🎯 Доступ: {item_name}\n"
        f"📅 Срок: {days} дней\n"
        f"⏰ До: {expires_at.strftime('%d.%m.%Y')}\n\n"
        "Выдать доступ?"
    )
    
    await callback.message.answer(
        text,
        reply_markup=get_confirm_keyboard(
            "admin:grant:confirm",
            f"admin:user:view:{user_id}"
        ),
        parse_mode="HTML"
    )


@router.callback_query(
    StateFilter(UserAdminState.grant_confirming),
    F.data == "admin:grant:confirm"
)
async def confirm_grant_access(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и выдача доступа."""
    data = await state.get_data()
    
    user_id = data.get('grant_user_id')
    telegram_id = data.get('grant_telegram_id')
    days = data.get('grant_days')
    channel_id = data.get('grant_channel_id')
    package_id = data.get('grant_package_id')
    
    expires_at = datetime.utcnow() + timedelta(days=days)
    
    try:
        # Создаём подписку
        subscription = await SubscriptionCRUD.create(
            user_telegram_id=telegram_id,
            channel_id=channel_id,
            package_id=package_id,
            expires_at=expires_at,
            is_active=True,
            is_manual=True
        )
        
        # Добавляем в каналы
        if channel_id:
            channel = await ChannelCRUD.get_by_id(channel_id)
            if channel:
                invite_link = await ChannelService.create_invite_link(
                    channel.telegram_id,
                    telegram_id
                )
                # Можно отправить пользователю уведомление
        
        elif package_id:
            package = await PackageCRUD.get_by_id(package_id)
            if package:
                for ch_id in package.channel_ids:
                    channel = await ChannelCRUD.get_by_id(ch_id)
                    if channel:
                        await ChannelService.create_invite_link(
                            channel.telegram_id,
                            telegram_id
                        )
        
        await state.clear()
        
        await callback.message.edit_text(
            "✅ <b>Доступ успешно выдан!</b>",
            reply_markup=get_back_keyboard(f"admin:user:view:{user_id}"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error granting access: {e}")
        await callback.answer("❌ Ошибка при выдаче доступа", show_alert=True)
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ❌ ОТЗЫВ ДОСТУПА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:user:revoke_sub:"))
async def confirm_revoke_subscription(callback: CallbackQuery, state: FSMContext):
    """Подтверждение отзыва подписки."""
    parts = callback.data.split(":")
    user_id = int(parts[3])
    sub_id = int(parts[4])
    
    subscription = await SubscriptionCRUD.get_by_id(sub_id)
    if not subscription:
        await callback.answer("❌ Подписка не найдена", show_alert=True)
        return
    
    # Определяем название
    if subscription.channel_id:
        channel = await ChannelCRUD.get_by_id(subscription.channel_id)
        item_name = channel.title if channel else f"Канал #{subscription.channel_id}"
    elif subscription.package_id:
        package = await PackageCRUD.get_by_id(subscription.package_id)
        item_name = package.name if package else f"Пакет #{subscription.package_id}"
    else:
        item_name = "—"
    
    text = (
        f"❌ <b>Отзыв доступа</b>\n\n"
        f"📦 {item_name}\n\n"
        "⚠️ Пользователь будет удалён из каналов.\n"
        "Продолжить?"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_keyboard(
            f"admin:user:revoke_confirm:{user_id}:{sub_id}",
            f"admin:user:subs:{user_id}"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user:revoke_confirm:"))
async def revoke_subscription(callback: CallbackQuery, state: FSMContext):
    """Отзыв подписки пользователя."""
    parts = callback.data.split(":")
    user_id = int(parts[3])
    sub_id = int(parts[4])
    
    subscription = await SubscriptionCRUD.get_by_id(sub_id)
    if not subscription:
        await callback.answer("❌ Подписка не найдена", show_alert=True)
        return
    
    user = await UserCRUD.get_by_id(user_id)
    
    try:
        # Деактивируем подписку
        await SubscriptionCRUD.update(sub_id, is_active=False)
        
        # Кикаем из каналов
        if subscription.channel_id:
            channel = await ChannelCRUD.get_by_id(subscription.channel_id)
            if channel and user:
                await ChannelService.kick_user(channel.telegram_id, user.telegram_id)
        
        elif subscription.package_id:
            package = await PackageCRUD.get_by_id(subscription.package_id)
            if package and user:
                for ch_id in package.channel_ids:
                    channel = await ChannelCRUD.get_by_id(ch_id)
                    if channel:
                        await ChannelService.kick_user(channel.telegram_id, user.telegram_id)
        
        await callback.answer("✅ Доступ отозван", show_alert=True)
        
        # Возвращаемся к подпискам
        await show_user_subscriptions(callback, state)
        
    except Exception as e:
        logger.error(f"Error revoking subscription {sub_id}: {e}")
        await callback.answer("❌ Ошибка при отзыве доступа", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 📤 ЭКСПОРТ ПОЛЬЗОВАТЕЛЕЙ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:users:export")
async def export_users(callback: CallbackQuery, state: FSMContext):
    """Экспорт списка пользователей."""
    await callback.answer("⏳ Формирование файла...", show_alert=False)
    
    try:
        users = await UserCRUD.get_all(limit=10000)
        
        # Формируем CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            'telegram_id', 'username', 'full_name', 'language',
            'is_banned', 'created_at', 'has_subscription'
        ])
        
        # Данные
        for user in users:
            has_sub = await SubscriptionCRUD.has_active(user.telegram_id)
            writer.writerow([
                user.telegram_id,
                user.username or '',
                user.full_name or '',
                user.language_code or 'ru',
                'yes' if user.is_banned else 'no',
                user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else '',
                'yes' if has_sub else 'no'
            ])
        
        # Отправляем файл
        from aiogram.types import BufferedInputFile
        
        file_data = output.getvalue().encode('utf-8-sig')
        filename = f"users_export_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
        
        document = BufferedInputFile(file_data, filename=filename)
        
        await callback.message.answer_document(
            document,
            caption=f"📤 Экспорт пользователей\n\n📊 Всего: {len(users)}"
        )
        
    except Exception as e:
        logger.error(f"Error exporting users: {e}")
        await callback.answer("❌ Ошибка при экспорте", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ФУНКЦИЯ ПОЛУЧЕНИЯ РОУТЕРА
# ═══════════════════════════════════════════════════════════════════════════════

def get_admin_users_router() -> Router:
    """Возвращает роутер управления пользователями."""
    return router
