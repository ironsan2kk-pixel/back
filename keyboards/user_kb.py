"""
═══════════════════════════════════════════════════════════════════════════════
⌨️ КЛАВИАТУРЫ ПОЛЬЗОВАТЕЛЯ
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import Optional, List, Dict, Any
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 ВЫБОР ЯЗЫКА
# ═══════════════════════════════════════════════════════════════════════════════

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    )
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 🏠 ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════════════════════

def get_main_menu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Главное меню пользователя."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {
            "catalog": "📢 Каталог каналов",
            "packages": "📦 Пакеты подписок",
            "profile": "👤 Мой профиль",
            "promo": "🎟️ Ввести промокод",
            "support": "💬 Поддержка",
            "language": "🌐 Сменить язык",
        },
        "en": {
            "catalog": "📢 Channel Catalog",
            "packages": "📦 Subscription Packages",
            "profile": "👤 My Profile",
            "promo": "🎟️ Enter Promo Code",
            "support": "💬 Support",
            "language": "🌐 Change Language",
        }
    }
    
    t = texts.get(lang, texts["ru"])
    
    builder.row(InlineKeyboardButton(text=t["catalog"], callback_data="menu:catalog"))
    builder.row(InlineKeyboardButton(text=t["packages"], callback_data="menu:packages"))
    builder.row(InlineKeyboardButton(text=t["profile"], callback_data="menu:profile"))
    builder.row(InlineKeyboardButton(text=t["promo"], callback_data="menu:promo"))
    builder.row(
        InlineKeyboardButton(text=t["support"], callback_data="menu:support"),
        InlineKeyboardButton(text=t["language"], callback_data="menu:language"),
    )
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 КАТАЛОГ КАНАЛОВ
# ═══════════════════════════════════════════════════════════════════════════════

def get_catalog_keyboard(
    channels: List[Dict[str, Any]], 
    lang: str = "ru",
    page: int = 0,
    per_page: int = 5
) -> InlineKeyboardMarkup:
    """Клавиатура каталога каналов с пагинацией."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {"back": "◀️ Назад", "prev": "⬅️", "next": "➡️"},
        "en": {"back": "◀️ Back", "prev": "⬅️", "next": "➡️"}
    }
    t = texts.get(lang, texts["ru"])
    
    # Пагинация
    total_pages = (len(channels) + per_page - 1) // per_page if channels else 1
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_channels = channels[start_idx:end_idx]
    
    # Кнопки каналов
    for channel in page_channels:
        name = channel.get("name_en" if lang == "en" and channel.get("name_en") else "name_ru", "Channel")
        price = channel.get("price_1_month", 0)
        emoji = channel.get("emoji", "📢")
        
        btn_text = f"{emoji} {name} — ${price}/мес" if lang == "ru" else f"{emoji} {name} — ${price}/mo"
        builder.row(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"channel:{channel['id']}"
        ))
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=t["prev"], callback_data=f"catalog:page:{page-1}"))
    
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page+1}/{total_pages}",
            callback_data="catalog:page:current"
        ))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=t["next"], callback_data=f"catalog:page:{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопка назад
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:back"))
    
    return builder.as_markup()


def get_channel_detail_keyboard(
    channel_id: int,
    periods: List[Dict[str, Any]],
    lang: str = "ru",
    has_subscription: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура детальной страницы канала с выбором периода."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {
            "subscribed": "✅ Вы подписаны",
            "back": "◀️ Назад к каталогу",
            "month_1": "1 месяц",
            "month_3": "3 месяца",
            "month_6": "6 месяцев",
            "month_12": "12 месяцев",
            "forever": "Навсегда",
        },
        "en": {
            "subscribed": "✅ You are subscribed",
            "back": "◀️ Back to Catalog",
            "month_1": "1 month",
            "month_3": "3 months",
            "month_6": "6 months",
            "month_12": "12 months",
            "forever": "Forever",
        }
    }
    t = texts.get(lang, texts["ru"])
    
    if has_subscription:
        builder.row(InlineKeyboardButton(text=t["subscribed"], callback_data="channel:already_subscribed"))
    else:
        # Кнопки периодов
        period_names = {
            1: t["month_1"],
            3: t["month_3"],
            6: t["month_6"],
            12: t["month_12"],
            0: t["forever"],
        }
        
        for period in periods:
            months = period.get("months", 1)
            price = period.get("price", 0)
            discount = period.get("discount", 0)
            
            name = period_names.get(months, f"{months} мес." if lang == "ru" else f"{months} mo.")
            
            if discount > 0:
                btn_text = f"{name} — ${price} (-{discount}%)"
            else:
                btn_text = f"{name} — ${price}"
            
            builder.row(InlineKeyboardButton(
                text=btn_text,
                callback_data=f"subscribe:{channel_id}:{months}"
            ))
    
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:catalog"))
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ПАКЕТЫ ПОДПИСОК
# ═══════════════════════════════════════════════════════════════════════════════

def get_packages_keyboard(
    packages: List[Dict[str, Any]],
    lang: str = "ru",
    page: int = 0,
    per_page: int = 5
) -> InlineKeyboardMarkup:
    """Клавиатура пакетов подписок."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {"back": "◀️ Назад", "prev": "⬅️", "next": "➡️"},
        "en": {"back": "◀️ Back", "prev": "⬅️", "next": "➡️"}
    }
    t = texts.get(lang, texts["ru"])
    
    # Пагинация
    total_pages = (len(packages) + per_page - 1) // per_page if packages else 1
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_packages = packages[start_idx:end_idx]
    
    for package in page_packages:
        name = package.get("name_en" if lang == "en" and package.get("name_en") else "name_ru", "Package")
        price = package.get("price", 0)
        channels_count = package.get("channels_count", 0)
        emoji = package.get("emoji", "📦")
        
        btn_text = f"{emoji} {name} ({channels_count} каналов) — ${price}" if lang == "ru" else f"{emoji} {name} ({channels_count} channels) — ${price}"
        builder.row(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"package:{package['id']}"
        ))
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=t["prev"], callback_data=f"packages:page:{page-1}"))
    
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page+1}/{total_pages}",
            callback_data="packages:page:current"
        ))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=t["next"], callback_data=f"packages:page:{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:back"))
    
    return builder.as_markup()


def get_package_detail_keyboard(
    package_id: int,
    periods: List[Dict[str, Any]],
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура детальной страницы пакета."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {
            "back": "◀️ Назад к пакетам",
            "month_1": "1 месяц",
            "month_3": "3 месяца",
            "month_6": "6 месяцев",
            "month_12": "12 месяцев",
            "forever": "Навсегда",
        },
        "en": {
            "back": "◀️ Back to Packages",
            "month_1": "1 month",
            "month_3": "3 months",
            "month_6": "6 months",
            "month_12": "12 months",
            "forever": "Forever",
        }
    }
    t = texts.get(lang, texts["ru"])
    
    period_names = {
        1: t["month_1"],
        3: t["month_3"],
        6: t["month_6"],
        12: t["month_12"],
        0: t["forever"],
    }
    
    for period in periods:
        months = period.get("months", 1)
        price = period.get("price", 0)
        discount = period.get("discount", 0)
        
        name = period_names.get(months, f"{months} мес." if lang == "ru" else f"{months} mo.")
        
        if discount > 0:
            btn_text = f"{name} — ${price} (-{discount}%)"
        else:
            btn_text = f"{name} — ${price}"
        
        builder.row(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"subscribe_package:{package_id}:{months}"
        ))
    
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:packages"))
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 💳 ОПЛАТА
# ═══════════════════════════════════════════════════════════════════════════════

def get_payment_keyboard(
    invoice_url: str,
    invoice_id: str,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура оплаты."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {
            "pay": "💳 Оплатить",
            "check": "🔄 Проверить оплату",
            "cancel": "❌ Отменить",
            "promo": "🎟️ Применить промокод",
        },
        "en": {
            "pay": "💳 Pay Now",
            "check": "🔄 Check Payment",
            "cancel": "❌ Cancel",
            "promo": "🎟️ Apply Promo Code",
        }
    }
    t = texts.get(lang, texts["ru"])
    
    builder.row(InlineKeyboardButton(text=t["pay"], url=invoice_url))
    builder.row(InlineKeyboardButton(text=t["promo"], callback_data=f"payment:promo:{invoice_id}"))
    builder.row(InlineKeyboardButton(text=t["check"], callback_data=f"payment:check:{invoice_id}"))
    builder.row(InlineKeyboardButton(text=t["cancel"], callback_data=f"payment:cancel:{invoice_id}"))
    
    return builder.as_markup()


def get_payment_success_keyboard(
    channel_username: Optional[str] = None,
    invite_link: Optional[str] = None,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура после успешной оплаты."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {
            "join": "📢 Перейти в канал",
            "profile": "👤 Мой профиль",
            "menu": "🏠 Главное меню",
        },
        "en": {
            "join": "📢 Join Channel",
            "profile": "👤 My Profile",
            "menu": "🏠 Main Menu",
        }
    }
    t = texts.get(lang, texts["ru"])
    
    if invite_link:
        builder.row(InlineKeyboardButton(text=t["join"], url=invite_link))
    elif channel_username:
        builder.row(InlineKeyboardButton(text=t["join"], url=f"https://t.me/{channel_username}"))
    
    builder.row(InlineKeyboardButton(text=t["profile"], callback_data="menu:profile"))
    builder.row(InlineKeyboardButton(text=t["menu"], callback_data="menu:back"))
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 👤 ПРОФИЛЬ
# ═══════════════════════════════════════════════════════════════════════════════

def get_profile_keyboard(
    subscriptions: List[Dict[str, Any]],
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура профиля пользователя."""
    builder = InlineKeyboardBuilder()

    texts = {
        "ru": {
            "subscriptions": "📋 Мои подписки",
            "history": "📜 История покупок",
            "extend": "🔄 Продлить подписку",
            "referrals": "👥 Реферальная программа",
            "back": "◀️ Назад",
        },
        "en": {
            "subscriptions": "📋 My Subscriptions",
            "history": "📜 Purchase History",
            "extend": "🔄 Extend Subscription",
            "referrals": "👥 Referral Program",
            "back": "◀️ Back",
        }
    }
    t = texts.get(lang, texts["ru"])

    builder.row(InlineKeyboardButton(text=t["subscriptions"], callback_data="profile:subscriptions"))
    builder.row(InlineKeyboardButton(text=t["history"], callback_data="profile:history"))
    builder.row(InlineKeyboardButton(text=t["referrals"], callback_data="profile:referrals"))

    if subscriptions:
        builder.row(InlineKeyboardButton(text=t["extend"], callback_data="profile:extend"))

    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:back"))

    return builder.as_markup()


def get_subscriptions_keyboard(
    subscriptions: List[Dict[str, Any]],
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура списка подписок."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {"back": "◀️ Назад", "extend": "🔄 Продлить"},
        "en": {"back": "◀️ Back", "extend": "🔄 Extend"}
    }
    t = texts.get(lang, texts["ru"])
    
    for sub in subscriptions:
        channel_name = sub.get("channel_name", "Channel")
        expires = sub.get("expires_at")
        is_forever = sub.get("is_forever", False)
        
        if is_forever:
            status = "♾️" if lang == "ru" else "♾️"
        elif expires:
            days_left = (expires - datetime.utcnow()).days
            status = f"({days_left}д)" if lang == "ru" else f"({days_left}d)"
        else:
            status = ""
        
        btn_text = f"📢 {channel_name} {status}"
        builder.row(
            InlineKeyboardButton(text=btn_text, callback_data=f"sub:view:{sub['id']}"),
            InlineKeyboardButton(text=t["extend"], callback_data=f"sub:extend:{sub['id']}")
        )
    
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:profile"))
    
    return builder.as_markup()


def get_purchase_history_keyboard(
    purchases: List[Dict[str, Any]],
    lang: str = "ru",
    page: int = 0,
    per_page: int = 10
) -> InlineKeyboardMarkup:
    """Клавиатура истории покупок."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {"back": "◀️ Назад", "prev": "⬅️", "next": "➡️"},
        "en": {"back": "◀️ Back", "prev": "⬅️", "next": "➡️"}
    }
    t = texts.get(lang, texts["ru"])
    
    # Пагинация
    total_pages = (len(purchases) + per_page - 1) // per_page if purchases else 1
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=t["prev"], callback_data=f"history:page:{page-1}"))
    
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(
            text=f"{page+1}/{total_pages}",
            callback_data="history:page:current"
        ))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=t["next"], callback_data=f"history:page:{page+1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:profile"))
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ПРОМОКОД
# ═══════════════════════════════════════════════════════════════════════════════

def get_promo_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура ввода промокода."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {"cancel": "❌ Отмена"},
        "en": {"cancel": "❌ Cancel"}
    }
    t = texts.get(lang, texts["ru"])
    
    builder.row(InlineKeyboardButton(text=t["cancel"], callback_data="menu:back"))
    
    return builder.as_markup()


def get_promo_result_keyboard(
    success: bool,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура результата применения промокода."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {
            "catalog": "📢 К каталогу",
            "back": "◀️ Назад",
            "try_again": "🔄 Попробовать снова",
        },
        "en": {
            "catalog": "📢 To Catalog",
            "back": "◀️ Back",
            "try_again": "🔄 Try Again",
        }
    }
    t = texts.get(lang, texts["ru"])
    
    if success:
        builder.row(InlineKeyboardButton(text=t["catalog"], callback_data="menu:catalog"))
    else:
        builder.row(InlineKeyboardButton(text=t["try_again"], callback_data="menu:promo"))
    
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:back"))
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 💬 ПОДДЕРЖКА
# ═══════════════════════════════════════════════════════════════════════════════

def get_support_keyboard(
    support_username: Optional[str] = None,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура поддержки."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {
            "faq": "❓ FAQ",
            "contact": "👨‍💻 Написать админу",
            "back": "◀️ Назад",
        },
        "en": {
            "faq": "❓ FAQ",
            "contact": "👨‍💻 Contact Admin",
            "back": "◀️ Back",
        }
    }
    t = texts.get(lang, texts["ru"])
    
    builder.row(InlineKeyboardButton(text=t["faq"], callback_data="support:faq"))
    
    if support_username:
        builder.row(InlineKeyboardButton(
            text=t["contact"],
            url=f"https://t.me/{support_username}"
        ))
    
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:back"))
    
    return builder.as_markup()


def get_faq_keyboard(
    questions: List[Dict[str, Any]],
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура FAQ."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {"back": "◀️ Назад"},
        "en": {"back": "◀️ Back"}
    }
    t = texts.get(lang, texts["ru"])
    
    for q in questions:
        question = q.get("question_en" if lang == "en" and q.get("question_en") else "question_ru", "Question")
        builder.row(InlineKeyboardButton(
            text=f"❓ {question[:40]}...",
            callback_data=f"faq:{q['id']}"
        ))
    
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="menu:support"))
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔙 ОБЩИЕ КНОПКИ
# ═══════════════════════════════════════════════════════════════════════════════

def get_back_button(callback_data: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопка назад."""
    builder = InlineKeyboardBuilder()
    
    text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    builder.row(InlineKeyboardButton(text=text, callback_data=callback_data))
    
    return builder.as_markup()


def get_confirm_keyboard(
    confirm_callback: str,
    cancel_callback: str,
    lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения."""
    builder = InlineKeyboardBuilder()
    
    texts = {
        "ru": {"confirm": "✅ Подтвердить", "cancel": "❌ Отмена"},
        "en": {"confirm": "✅ Confirm", "cancel": "❌ Cancel"}
    }
    t = texts.get(lang, texts["ru"])
    
    builder.row(
        InlineKeyboardButton(text=t["confirm"], callback_data=confirm_callback),
        InlineKeyboardButton(text=t["cancel"], callback_data=cancel_callback),
    )
    
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════════════════════

def remove_keyboard() -> ReplyKeyboardRemove:
    """Удалить reply-клавиатуру."""
    return ReplyKeyboardRemove()
