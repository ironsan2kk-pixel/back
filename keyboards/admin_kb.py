"""
Клавиатуры для административной панели
Чат 5.2 - Telegram бот продажи доступов к каналам

Содержит генераторы клавиатур для:
- Главное меню админки
- Каналы
- Пакеты
- Тарифы
- Промокодов
- Пользователей
- Статистики
- Рассылки
- Настроек
"""

from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.i18n import get_text


# ==================== ГЛАВНОЕ МЕНЮ АДМИНКИ ====================

def get_admin_main_menu() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📢 Каналы", callback_data="admin:channels"),
        InlineKeyboardButton(text="📦 Пакеты", callback_data="admin:packages")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Тарифы", callback_data="admin:pricing"),
        InlineKeyboardButton(text="🎟️ Промокоды", callback_data="admin:promos")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")
    )
    builder.row(
        InlineKeyboardButton(text="📨 Рассылка", callback_data="admin:broadcast"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin:settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh")
    )

    return builder.as_markup()


def get_channels_menu() -> InlineKeyboardMarkup:
    """Меню управления каналами."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Список каналов", callback_data="admin:channels:list")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin:channels:add")
    )
    builder.row(
        InlineKeyboardButton(text="🔢 Изменить порядок", callback_data="admin:channels:order")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")
    )

    return builder.as_markup()


def get_packages_menu() -> InlineKeyboardMarkup:
    """Меню управления пакетами."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Список пакетов", callback_data="admin:packages:list")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Создать пакет", callback_data="admin:packages:add")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")
    )

    return builder.as_markup()


def get_pricing_menu() -> InlineKeyboardMarkup:
    """Меню управления тарифами."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📢 Тарифы каналов", callback_data="admin:pricing:channels")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Тарифы пакетов", callback_data="admin:pricing:packages")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")
    )

    return builder.as_markup()


def get_promos_menu() -> InlineKeyboardMarkup:
    """Меню управления промокодами."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin:promo:create")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin:promo:list")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:promo:stats")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")
    )

    return builder.as_markup()


def get_users_menu() -> InlineKeyboardMarkup:
    """Меню управления пользователями."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Все пользователи", callback_data="admin:users:list:all")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Активные", callback_data="admin:users:list:active"),
        InlineKeyboardButton(text="🚫 Заблокированные", callback_data="admin:users:list:banned")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск", callback_data="admin:users:search")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")
    )

    return builder.as_markup()


def get_stats_menu() -> InlineKeyboardMarkup:
    """Меню статистики."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Общая", callback_data="admin:stats:general")
    )
    builder.row(
        InlineKeyboardButton(text="📢 По каналам", callback_data="admin:stats:channels"),
        InlineKeyboardButton(text="📦 По пакетам", callback_data="admin:stats:packages")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Финансы", callback_data="admin:stats:finance")
    )
    builder.row(
        InlineKeyboardButton(text="📤 Экспорт", callback_data="admin:stats:export")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")
    )

    return builder.as_markup()


def get_broadcast_menu() -> InlineKeyboardMarkup:
    """Меню рассылки."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✉️ Новая рассылка", callback_data="admin:broadcast:new")
    )
    builder.row(
        InlineKeyboardButton(text="📋 История", callback_data="admin:broadcast:history")
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Запланированные", callback_data="admin:broadcast:scheduled")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")
    )

    return builder.as_markup()


def get_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="⚙️ Общие", callback_data="admin:settings:general")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Оплата", callback_data="admin:settings:payment")
    )
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="admin:settings:notifications")
    )
    builder.row(
        InlineKeyboardButton(text="👑 Администраторы", callback_data="admin:settings:admins")
    )
    builder.row(
        InlineKeyboardButton(text="💾 Бэкап", callback_data="admin:settings:backup")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")
    )

    return builder.as_markup()


# ==================== КАНАЛЫ ====================

def get_channels_list_keyboard(
    channels: list,
    page: int = 0,
    per_page: int = 10
) -> InlineKeyboardMarkup:
    """Список каналов с пагинацией."""
    builder = InlineKeyboardBuilder()

    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_channels = channels[start_idx:end_idx]

    for channel in page_channels:
        status = "✅" if channel.get("is_active") else "❌"
        subs = channel.get("subscribers_count", 0)
        name = channel.get("name_ru", "—")[:20]
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {name} ({subs})",
                callback_data=f"admin:channels:view:{channel.get('id')}"
            )
        )

    # Пагинация
    nav_buttons = []
    total_pages = (len(channels) + per_page - 1) // per_page

    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"admin:channels:list:{page - 1}")
        )

    if total_pages > 1:
        nav_buttons.append(
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
        )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"admin:channels:list:{page + 1}")
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="admin:channels:add")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin:channels")
    )

    return builder.as_markup()


def get_channel_detail_keyboard(channel_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Детали канала."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ Название RU",
            callback_data=f"admin:channels:edit:{channel_id}:name_ru"
        ),
        InlineKeyboardButton(
            text="✏️ Название EN",
            callback_data=f"admin:channels:edit:{channel_id}:name_en"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Описание RU",
            callback_data=f"admin:channels:edit:{channel_id}:desc_ru"
        ),
        InlineKeyboardButton(
            text="📝 Описание EN",
            callback_data=f"admin:channels:edit:{channel_id}:desc_en"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🖼️ Изображение",
            callback_data=f"admin:channels:edit:{channel_id}:image"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎁 Пробный период",
            callback_data=f"admin:channels:trial:{channel_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Тарифы",
            callback_data=f"admin:pricing:channel:{channel_id}"
        )
    )

    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="❌ Деактивировать",
                callback_data=f"admin:channels:deactivate:{channel_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Активировать",
                callback_data=f"admin:channels:activate:{channel_id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"admin:channels:delete:{channel_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ К списку", callback_data="admin:channels:list")
    )

    return builder.as_markup()


def get_channel_trial_keyboard(
    channel_id: int,
    is_enabled: bool,
    days: int
) -> InlineKeyboardMarkup:
    """Настройки пробного периода."""
    builder = InlineKeyboardBuilder()

    toggle_text = "🔴 Выключить" if is_enabled else "🟢 Включить"
    builder.row(
        InlineKeyboardButton(
            text=toggle_text,
            callback_data=f"admin:channels:trial:toggle:{channel_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"📅 Дней: {days}",
            callback_data=f"admin:channels:trial:days:{channel_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"admin:channels:view:{channel_id}"
        )
    )

    return builder.as_markup()


def get_channel_order_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Список каналов для изменения порядка."""
    builder = InlineKeyboardBuilder()

    for i, channel in enumerate(channels, 1):
        builder.row(
            InlineKeyboardButton(
                text=f"{i}. {channel.get('name_ru', '—')[:25]}",
                callback_data=f"admin:channels:order:select:{channel.get('id')}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="admin:channels:order:save")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Отмена", callback_data="admin:channels")
    )

    return builder.as_markup()


def get_channel_position_keyboard(
    channel_id: int,
    current_pos: int,
    total: int
) -> InlineKeyboardMarkup:
    """Выбор позиции для канала."""
    builder = InlineKeyboardBuilder()

    # Генерируем кнопки позиций
    buttons = []
    for i in range(1, total + 1):
        text = f"[{i}]" if i == current_pos else str(i)
        buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"admin:channels:order:move:{channel_id}:{i}"
            )
        )

    # Размещаем по 5 в ряд
    for i in range(0, len(buttons), 5):
        builder.row(*buttons[i:i + 5])

    builder.row(
        InlineKeyboardButton(text="◀️ Отмена", callback_data="admin:channels:order")
    )

    return builder.as_markup()


def get_confirm_cancel_keyboard(
    confirm_callback: str,
    cancel_callback: str,
    confirm_text: str = "✅ Подтвердить",
    cancel_text: str = "❌ Отмена"
) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения/отмены."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text=confirm_text, callback_data=confirm_callback)
    )
    builder.row(
        InlineKeyboardButton(text=cancel_text, callback_data=cancel_callback)
    )

    return builder.as_markup()


def get_back_button(
    callback_data: str,
    text: str = "◀️ Назад"
) -> InlineKeyboardMarkup:
    """Кнопка назад."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=text, callback_data=callback_data)
    )
    return builder.as_markup()


def get_skip_button(callback_data: str) -> InlineKeyboardButton:
    """Кнопка пропуска шага."""
    return InlineKeyboardButton(text="⏭️ Пропустить", callback_data=callback_data)


# ==================== ОБЩИЕ КЛАВИАТУРЫ ====================

def get_back_kb(lang: str, callback_data: str = "admin:menu") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой назад.
    
    Args:
        lang: Код языка
        callback_data: Callback для кнопки назад
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_back", lang),
        callback_data=callback_data
    )
    return builder.as_markup()


def get_confirm_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_confirm", lang),
            callback_data="admin:confirm"
        ),
        InlineKeyboardButton(
            text=get_text("btn_cancel", lang),
            callback_data="admin:cancel"
        )
    )
    return builder.as_markup()


def get_cancel_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_cancel", lang),
        callback_data="admin:cancel"
    )
    return builder.as_markup()


# ==================== ПРОМОКОДЫ ====================

def get_promo_menu_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Главное меню промокодов.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="➕ " + get_text("btn_create_promo", lang),
            callback_data="admin:promo:create"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("btn_list_promos", lang),
            callback_data="admin:promo:list"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 " + get_text("btn_promo_stats", lang),
            callback_data="admin:promo:stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:menu"
        )
    )
    return builder.as_markup()


def get_promo_create_type_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Выбор типа создания промокода.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ " + get_text("btn_manual_code", lang),
            callback_data="admin:promo:create:manual"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎲 " + get_text("btn_auto_code", lang),
            callback_data="admin:promo:create:auto"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📦 " + get_text("btn_bulk_codes", lang),
            callback_data="admin:promo:create:bulk"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:promo"
        )
    )
    return builder.as_markup()


def get_promo_discount_type_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Выбор типа скидки.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💯 " + get_text("btn_discount_percent", lang),
            callback_data="admin:promo:discount:percent"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💵 " + get_text("btn_discount_fixed", lang),
            callback_data="admin:promo:discount:fixed"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📅 " + get_text("btn_discount_days", lang),
            callback_data="admin:promo:discount:days"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:promo:create"
        )
    )
    return builder.as_markup()


def get_promo_target_kb(
    lang: str,
    channels: list = None,
    packages: list = None
) -> InlineKeyboardMarkup:
    """
    Выбор цели промокода.
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🌐 " + get_text("btn_target_all", lang),
            callback_data="admin:promo:target:all"
        )
    )
    
    if channels:
        for channel in channels[:5]:
            builder.row(
                InlineKeyboardButton(
                    text=f"📺 {channel.name}",
                    callback_data=f"admin:promo:target:channel:{channel.id}"
                )
            )
    
    if packages:
        for package in packages[:5]:
            builder.row(
                InlineKeyboardButton(
                    text=f"📦 {package.name}",
                    callback_data=f"admin:promo:target:package:{package.id}"
                )
            )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:promo:create"
        )
    )
    return builder.as_markup()


def get_promo_list_kb(
    promos: list,
    page: int,
    total_pages: int,
    lang: str
) -> InlineKeyboardMarkup:
    """
    Список промокодов с пагинацией.
    """
    builder = InlineKeyboardBuilder()
    
    for promo in promos:
        status = "✅" if promo.is_active else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {promo.code}",
                callback_data=f"admin:promo:view:{promo.id}"
            )
        )
    
    # Пагинация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"admin:promo:list:{page-1}")
        )
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"admin:promo:list:{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:promo"
        )
    )
    return builder.as_markup()


def get_promo_view_kb(promo_id: int, is_active: bool, lang: str) -> InlineKeyboardMarkup:
    """
    Просмотр промокода.
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✏️ " + get_text("btn_edit", lang),
            callback_data=f"admin:promo:edit:{promo_id}"
        )
    )
    
    toggle_text = get_text("btn_deactivate", lang) if is_active else get_text("btn_activate", lang)
    builder.row(
        InlineKeyboardButton(
            text=("🔴 " if is_active else "🟢 ") + toggle_text,
            callback_data=f"admin:promo:toggle:{promo_id}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🗑 " + get_text("btn_delete", lang),
            callback_data=f"admin:promo:delete:{promo_id}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:promo:list"
        )
    )
    return builder.as_markup()


def get_promo_edit_kb(promo_id: int, lang: str) -> InlineKeyboardMarkup:
    """
    Меню редактирования промокода.
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📝 " + get_text("btn_edit_code", lang),
            callback_data=f"admin:promo:edit:code:{promo_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 " + get_text("btn_edit_discount", lang),
            callback_data=f"admin:promo:edit:discount:{promo_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔢 " + get_text("btn_edit_limit", lang),
            callback_data=f"admin:promo:edit:limit:{promo_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📅 " + get_text("btn_edit_expiry", lang),
            callback_data=f"admin:promo:edit:expiry:{promo_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data=f"admin:promo:view:{promo_id}"
        )
    )
    return builder.as_markup()


def get_back_to_promo_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Возврат в меню промокодов.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_back", lang),
        callback_data="admin:promo"
    )
    return builder.as_markup()


# ==================== ПОЛЬЗОВАТЕЛИ ====================

def get_users_menu_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Главное меню управления пользователями.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("btn_all_users", lang),
            callback_data="admin:users:list:all"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ " + get_text("btn_active_users", lang),
            callback_data="admin:users:list:active"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🚫 " + get_text("btn_banned_users", lang),
            callback_data="admin:users:list:banned"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🆕 " + get_text("btn_new_users", lang),
            callback_data="admin:users:list:new"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔍 " + get_text("btn_search_user", lang),
            callback_data="admin:users:search"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📤 " + get_text("btn_export_users", lang),
            callback_data="admin:users:export"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:menu"
        )
    )
    return builder.as_markup()


def get_users_list_kb(
    users: list,
    page: int,
    total_pages: int,
    filter_type: str,
    lang: str
) -> InlineKeyboardMarkup:
    """
    Список пользователей с пагинацией.
    """
    builder = InlineKeyboardBuilder()
    
    for user in users:
        status = "🚫" if user.is_banned else "👤"
        name = user.username or user.full_name or str(user.telegram_id)
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {name[:20]}",
                callback_data=f"admin:users:view:{user.id}"
            )
        )
    
    # Пагинация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"admin:users:list:{filter_type}:{page-1}"
            )
        )
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"admin:users:list:{filter_type}:{page+1}"
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:users"
        )
    )
    return builder.as_markup()


def get_user_view_kb(user_id: int, is_banned: bool, lang: str) -> InlineKeyboardMarkup:
    """
    Просмотр профиля пользователя.
    """
    builder = InlineKeyboardBuilder()
    
    if is_banned:
        builder.row(
            InlineKeyboardButton(
                text="✅ " + get_text("btn_unban", lang),
                callback_data=f"admin:users:unban:{user_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🚫 " + get_text("btn_ban", lang),
                callback_data=f"admin:users:ban:{user_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🎁 " + get_text("btn_grant_access", lang),
            callback_data=f"admin:users:grant:{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("btn_subscriptions", lang),
            callback_data=f"admin:users:subs:{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💳 " + get_text("btn_payments", lang),
            callback_data=f"admin:users:payments:{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:users"
        )
    )
    return builder.as_markup()


def get_grant_type_kb(user_id: int, lang: str) -> InlineKeyboardMarkup:
    """
    Выбор типа выдачи доступа.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📺 " + get_text("btn_grant_channel", lang),
            callback_data=f"admin:users:grant:channel:{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📦 " + get_text("btn_grant_package", lang),
            callback_data=f"admin:users:grant:package:{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data=f"admin:users:view:{user_id}"
        )
    )
    return builder.as_markup()


def get_grant_channels_kb(
    channels: list,
    user_id: int,
    lang: str
) -> InlineKeyboardMarkup:
    """
    Список каналов для выдачи доступа.
    """
    builder = InlineKeyboardBuilder()
    
    for channel in channels:
        builder.row(
            InlineKeyboardButton(
                text=f"📺 {channel.name}",
                callback_data=f"admin:users:grant:ch:{channel.id}:{user_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data=f"admin:users:grant:{user_id}"
        )
    )
    return builder.as_markup()


def get_grant_packages_kb(
    packages: list,
    user_id: int,
    lang: str
) -> InlineKeyboardMarkup:
    """
    Список пакетов для выдачи доступа.
    """
    builder = InlineKeyboardBuilder()
    
    for package in packages:
        builder.row(
            InlineKeyboardButton(
                text=f"📦 {package.name}",
                callback_data=f"admin:users:grant:pk:{package.id}:{user_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data=f"admin:users:grant:{user_id}"
        )
    )
    return builder.as_markup()


def get_grant_duration_kb(
    grant_type: str,
    target_id: int,
    user_id: int,
    lang: str
) -> InlineKeyboardMarkup:
    """
    Выбор длительности доступа.
    """
    builder = InlineKeyboardBuilder()
    
    prefix = f"admin:users:grant:dur:{grant_type}:{target_id}:{user_id}"
    
    builder.row(
        InlineKeyboardButton(text="7 дней", callback_data=f"{prefix}:7"),
        InlineKeyboardButton(text="30 дней", callback_data=f"{prefix}:30")
    )
    builder.row(
        InlineKeyboardButton(text="90 дней", callback_data=f"{prefix}:90"),
        InlineKeyboardButton(text="180 дней", callback_data=f"{prefix}:180")
    )
    builder.row(
        InlineKeyboardButton(text="365 дней", callback_data=f"{prefix}:365"),
        InlineKeyboardButton(text="✏️ Своё", callback_data=f"{prefix}:custom")
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data=f"admin:users:view:{user_id}"
        )
    )
    return builder.as_markup()


def get_user_subs_kb(
    subscriptions: list,
    user_id: int,
    lang: str
) -> InlineKeyboardMarkup:
    """
    Список подписок пользователя.
    """
    builder = InlineKeyboardBuilder()
    
    for sub in subscriptions:
        status = "✅" if sub.is_active else "❌"
        name = sub.channel.name if sub.channel else (sub.package.name if sub.package else f"#{sub.id}")
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {name[:20]}",
                callback_data=f"admin:users:sub:view:{sub.id}:{user_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data=f"admin:users:view:{user_id}"
        )
    )
    return builder.as_markup()


def get_back_to_users_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Возврат в меню пользователей.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_back", lang),
        callback_data="admin:users"
    )
    return builder.as_markup()


# ==================== СТАТИСТИКА ====================

def get_stats_menu_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Главное меню статистики.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📊 " + get_text("btn_general_stats", lang),
            callback_data="admin:stats:general"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📺 " + get_text("btn_channel_stats", lang),
            callback_data="admin:stats:channels"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📦 " + get_text("btn_package_stats", lang),
            callback_data="admin:stats:packages"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 " + get_text("btn_finance_stats", lang),
            callback_data="admin:stats:finance"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📤 " + get_text("btn_export_stats", lang),
            callback_data="admin:stats:export"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:menu"
        )
    )
    return builder.as_markup()


def get_stats_period_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Выбор периода статистики.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=get_text("period_today", lang),
            callback_data="admin:stats:period:today"
        ),
        InlineKeyboardButton(
            text=get_text("period_week", lang),
            callback_data="admin:stats:period:week"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("period_month", lang),
            callback_data="admin:stats:period:month"
        ),
        InlineKeyboardButton(
            text=get_text("period_quarter", lang),
            callback_data="admin:stats:period:quarter"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("period_year", lang),
            callback_data="admin:stats:period:year"
        ),
        InlineKeyboardButton(
            text=get_text("period_all", lang),
            callback_data="admin:stats:period:all"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:stats"
        )
    )
    return builder.as_markup()


def get_stats_channels_kb(channels: list, lang: str) -> InlineKeyboardMarkup:
    """
    Список каналов для статистики.
    """
    builder = InlineKeyboardBuilder()
    
    for channel in channels:
        builder.row(
            InlineKeyboardButton(
                text=f"📺 {channel.name}",
                callback_data=f"admin:stats:channel:{channel.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:stats"
        )
    )
    return builder.as_markup()


def get_stats_packages_kb(packages: list, lang: str) -> InlineKeyboardMarkup:
    """
    Список пакетов для статистики.
    """
    builder = InlineKeyboardBuilder()
    
    for package in packages:
        builder.row(
            InlineKeyboardButton(
                text=f"📦 {package.name}",
                callback_data=f"admin:stats:package:{package.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:stats"
        )
    )
    return builder.as_markup()


def get_stats_export_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Меню экспорта статистики.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="👥 " + get_text("btn_export_users", lang),
            callback_data="admin:stats:export:users"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💳 " + get_text("btn_export_payments", lang),
            callback_data="admin:stats:export:payments"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("btn_export_subscriptions", lang),
            callback_data="admin:stats:export:subscriptions"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎟 " + get_text("btn_export_promos", lang),
            callback_data="admin:stats:export:promos"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📄 " + get_text("btn_full_report", lang),
            callback_data="admin:stats:export:full_report"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:stats"
        )
    )
    return builder.as_markup()


def get_back_to_stats_kb(
    lang: str,
    back_to: str = "admin:stats"
) -> InlineKeyboardMarkup:
    """
    Возврат в статистику.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_back", lang),
        callback_data=back_to
    )
    return builder.as_markup()


# ==================== РАССЫЛКА ====================

def get_broadcast_menu_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Главное меню рассылки.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✉️ " + get_text("btn_new_broadcast", lang),
            callback_data="admin:broadcast:new"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 " + get_text("btn_broadcast_history", lang),
            callback_data="admin:broadcast:history"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏰ " + get_text("btn_scheduled_broadcasts", lang),
            callback_data="admin:broadcast:scheduled"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:menu"
        )
    )
    return builder.as_markup()


def get_broadcast_target_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Выбор целевой аудитории рассылки.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="👥 " + get_text("btn_target_all", lang),
            callback_data="admin:broadcast:target:all"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ " + get_text("btn_target_active", lang),
            callback_data="admin:broadcast:target:active"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="😴 " + get_text("btn_target_inactive", lang),
            callback_data="admin:broadcast:target:inactive"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🆕 " + get_text("btn_target_new", lang),
            callback_data="admin:broadcast:target:new"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📺 " + get_text("btn_target_channel", lang),
            callback_data="admin:broadcast:target:channel"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📦 " + get_text("btn_target_package", lang),
            callback_data="admin:broadcast:target:package"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:broadcast"
        )
    )
    return builder.as_markup()


def get_broadcast_channels_kb(channels: list, lang: str) -> InlineKeyboardMarkup:
    """
    Список каналов для рассылки.
    """
    builder = InlineKeyboardBuilder()
    
    for channel in channels:
        builder.row(
            InlineKeyboardButton(
                text=f"📺 {channel.name}",
                callback_data=f"admin:broadcast:channel:{channel.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:broadcast:new"
        )
    )
    return builder.as_markup()


def get_broadcast_packages_kb(packages: list, lang: str) -> InlineKeyboardMarkup:
    """
    Список пакетов для рассылки.
    """
    builder = InlineKeyboardBuilder()
    
    for package in packages:
        builder.row(
            InlineKeyboardButton(
                text=f"📦 {package.name}",
                callback_data=f"admin:broadcast:package:{package.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:broadcast:new"
        )
    )
    return builder.as_markup()


def get_broadcast_media_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Добавление медиа к рассылке.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⏭ " + get_text("btn_skip_media", lang),
            callback_data="admin:broadcast:skip_media"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_cancel", lang),
            callback_data="admin:broadcast"
        )
    )
    return builder.as_markup()


def get_broadcast_confirm_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Подтверждение рассылки.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🚀 " + get_text("btn_send_now", lang),
            callback_data="admin:broadcast:send_now"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏰ " + get_text("btn_schedule", lang),
            callback_data="admin:broadcast:schedule"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ " + get_text("btn_cancel", lang),
            callback_data="admin:broadcast:cancel"
        )
    )
    return builder.as_markup()


def get_broadcast_schedule_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Выбор времени отложенной рассылки.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 час", callback_data="admin:broadcast:schedule:1h"),
        InlineKeyboardButton(text="3 часа", callback_data="admin:broadcast:schedule:3h")
    )
    builder.row(
        InlineKeyboardButton(text="6 часов", callback_data="admin:broadcast:schedule:6h"),
        InlineKeyboardButton(text="12 часов", callback_data="admin:broadcast:schedule:12h")
    )
    builder.row(
        InlineKeyboardButton(text="24 часа", callback_data="admin:broadcast:schedule:24h")
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:broadcast:new"
        )
    )
    return builder.as_markup()


def get_back_to_broadcast_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Возврат в меню рассылки.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_back", lang),
        callback_data="admin:broadcast"
    )
    return builder.as_markup()


# ==================== НАСТРОЙКИ ====================

def get_settings_menu_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Главное меню настроек.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⚙️ " + get_text("btn_general_settings", lang),
            callback_data="admin:settings:general"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💳 " + get_text("btn_payment_settings", lang),
            callback_data="admin:settings:payment"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔔 " + get_text("btn_notification_settings", lang),
            callback_data="admin:settings:notifications"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👑 " + get_text("btn_admins_settings", lang),
            callback_data="admin:settings:admins"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💾 " + get_text("btn_backup_settings", lang),
            callback_data="admin:settings:backup"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:menu"
        )
    )
    return builder.as_markup()


def get_settings_general_kb(lang: str, maintenance: bool = False) -> InlineKeyboardMarkup:
    """
    Общие настройки.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📝 " + get_text("btn_edit_bot_name", lang),
            callback_data="admin:settings:edit:bot_name"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👋 " + get_text("btn_edit_welcome", lang),
            callback_data="admin:settings:edit:welcome"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💬 " + get_text("btn_edit_support", lang),
            callback_data="admin:settings:edit:support"
        )
    )
    
    maintenance_text = "🔴 Выкл. обслуживание" if maintenance else "🟢 Вкл. обслуживание"
    builder.row(
        InlineKeyboardButton(
            text=maintenance_text,
            callback_data="admin:settings:toggle:maintenance"
        )
    )
    
    builder.row(
        InlineKeyboardButton(text="🇷🇺 RU", callback_data="admin:settings:lang:ru"),
        InlineKeyboardButton(text="🇬🇧 EN", callback_data="admin:settings:lang:en")
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:settings"
        )
    )
    return builder.as_markup()


def get_settings_payment_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Настройки оплаты.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔑 " + get_text("btn_edit_crypto_token", lang),
            callback_data="admin:settings:edit:crypto_token"
        )
    )
    builder.row(
        InlineKeyboardButton(text="USDT", callback_data="admin:settings:currency:USDT"),
        InlineKeyboardButton(text="BTC", callback_data="admin:settings:currency:BTC"),
        InlineKeyboardButton(text="ETH", callback_data="admin:settings:currency:ETH")
    )
    builder.row(
        InlineKeyboardButton(
            text="⏱ " + get_text("btn_edit_timeout", lang),
            callback_data="admin:settings:edit:timeout"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:settings"
        )
    )
    return builder.as_markup()


def get_settings_notifications_kb(
    lang: str,
    new_user: bool = True,
    new_payment: bool = True,
    sub_end: bool = True
) -> InlineKeyboardMarkup:
    """
    Настройки уведомлений.
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{'✅' if new_user else '❌'} Новые пользователи",
            callback_data="admin:settings:toggle:notify_new_user"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{'✅' if new_payment else '❌'} Новые платежи",
            callback_data="admin:settings:toggle:notify_new_payment"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{'✅' if sub_end else '❌'} Окончание подписки",
            callback_data="admin:settings:toggle:notify_subscription_end"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📅 Дней до уведомления",
            callback_data="admin:settings:edit:notify_days"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💬 Чат для уведомлений",
            callback_data="admin:settings:edit:admin_chat"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:settings"
        )
    )
    return builder.as_markup()


def get_settings_admins_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Управление администраторами.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="➕ " + get_text("btn_add_admin", lang),
            callback_data="admin:settings:add_admin"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="➖ " + get_text("btn_remove_admin", lang),
            callback_data="admin:settings:remove_admin"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:settings"
        )
    )
    return builder.as_markup()


def get_settings_backup_kb(lang: str) -> InlineKeyboardMarkup:
    """
    Резервное копирование.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📥 " + get_text("btn_create_backup", lang),
            callback_data="admin:settings:backup:create"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📤 " + get_text("btn_restore_backup", lang),
            callback_data="admin:settings:backup:restore"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=get_text("btn_back", lang),
            callback_data="admin:settings"
        )
    )
    return builder.as_markup()


def get_back_to_settings_kb(
    lang: str,
    back_to: str = "admin:settings"
) -> InlineKeyboardMarkup:
    """
    Возврат в настройки.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_back", lang),
        callback_data=back_to
    )
    return builder.as_markup()
