"""
═══════════════════════════════════════════════════════════════════════════════
📢 ХЕНДЛЕР КАТАЛОГА КАНАЛОВ И ПАКЕТОВ
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging

from database.crud import (
    UserCRUD,
    ChannelCRUD,
    PackageCRUD,
    SubscriptionCRUD,
    PricingCRUD,
)
from keyboards.user_kb import (
    get_channel_detail_keyboard,
    get_package_detail_keyboard,
    get_main_menu_keyboard,
    get_back_button,
)
from utils.i18n import I18n

logger = logging.getLogger(__name__)

router = Router(name="catalog")


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 ДЕТАЛЬНАЯ СТРАНИЦА КАНАЛА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("channel:"))
async def callback_channel_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Показать детальную информацию о канале."""
    data_parts = callback.data.split(":")
    
    # Обработка специальных callback'ов
    if len(data_parts) > 1 and data_parts[1] == "already_subscribed":
        await callback.answer(
            i18n.get("already_subscribed_alert", "ru"),
            show_alert=True
        )
        return
    
    try:
        channel_id = int(data_parts[1])
    except (ValueError, IndexError):
        await callback.answer("Error", show_alert=True)
        return
    
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    await show_channel_detail(callback.message, session, channel_id, i18n, lang, edit=True)


async def show_channel_detail(
    message: Message,
    session: AsyncSession,
    channel_id: int,
    i18n: I18n,
    lang: str,
    edit: bool = False
):
    """
    Показать детальную информацию о канале.
    
    Используется как из callback_query, так и из deep link.
    """
    # Получаем канал
    channel = await ChannelCRUD.get_by_id(session, channel_id)
    
    if not channel or not channel.is_active:
        text = i18n.get("channel_not_found", lang)
        if edit:
            await message.edit_text(text, reply_markup=get_main_menu_keyboard(lang))
        else:
            await message.answer(text, reply_markup=get_main_menu_keyboard(lang))
        return
    
    # Получаем пользователя для проверки подписки
    user = await UserCRUD.get_by_telegram_id(session, message.chat.id)
    has_subscription = False
    
    if user:
        subscription = await SubscriptionCRUD.get_user_channel_subscription(
            session, user.id, channel_id
        )
        has_subscription = subscription is not None and subscription.is_active
    
    # Получаем ценовые периоды
    periods = _get_channel_periods(channel)
    
    # Формируем описание канала
    name = channel.name_en if lang == "en" and channel.name_en else channel.name_ru
    description = channel.description_en if lang == "en" and channel.description_en else channel.description_ru
    
    emoji = channel.emoji or "📢"
    
    # Информация о подписчиках (если есть)
    subscribers_text = ""
    if channel.subscribers_count:
        subscribers_text = f"\n👥 {i18n.get('subscribers', lang)}: {channel.subscribers_count:,}"
    
    text = i18n.get(
        "channel_detail",
        lang,
        emoji=emoji,
        name=name,
        description=description or i18n.get("no_description", lang),
        subscribers=subscribers_text,
    )
    
    keyboard = get_channel_detail_keyboard(
        channel_id,
        periods,
        lang,
        has_subscription=has_subscription
    )
    
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


def _get_channel_periods(channel) -> List[dict]:
    """Получить доступные периоды подписки для канала."""
    periods = []
    
    # 1 месяц
    if channel.price_1_month and channel.price_1_month > 0:
        periods.append({
            "months": 1,
            "price": channel.price_1_month,
            "discount": 0,
        })
    
    # 3 месяца
    if channel.price_3_month and channel.price_3_month > 0:
        base_price = (channel.price_1_month or 0) * 3
        discount = int(((base_price - channel.price_3_month) / base_price * 100)) if base_price > 0 else 0
        periods.append({
            "months": 3,
            "price": channel.price_3_month,
            "discount": max(0, discount),
        })
    
    # 6 месяцев
    if channel.price_6_month and channel.price_6_month > 0:
        base_price = (channel.price_1_month or 0) * 6
        discount = int(((base_price - channel.price_6_month) / base_price * 100)) if base_price > 0 else 0
        periods.append({
            "months": 6,
            "price": channel.price_6_month,
            "discount": max(0, discount),
        })
    
    # 12 месяцев
    if channel.price_12_month and channel.price_12_month > 0:
        base_price = (channel.price_1_month or 0) * 12
        discount = int(((base_price - channel.price_12_month) / base_price * 100)) if base_price > 0 else 0
        periods.append({
            "months": 12,
            "price": channel.price_12_month,
            "discount": max(0, discount),
        })
    
    # Навсегда
    if channel.price_forever and channel.price_forever > 0:
        periods.append({
            "months": 0,  # 0 = навсегда
            "price": channel.price_forever,
            "discount": 0,
        })
    
    return periods


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ДЕТАЛЬНАЯ СТРАНИЦА ПАКЕТА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("package:"))
async def callback_package_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Показать детальную информацию о пакете."""
    try:
        package_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Error", show_alert=True)
        return
    
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    await show_package_detail(callback.message, session, package_id, i18n, lang, edit=True)


async def show_package_detail(
    message: Message,
    session: AsyncSession,
    package_id: int,
    i18n: I18n,
    lang: str,
    edit: bool = False
):
    """
    Показать детальную информацию о пакете.
    
    Используется как из callback_query, так и из deep link.
    """
    # Получаем пакет
    package = await PackageCRUD.get_by_id(session, package_id)
    
    if not package or not package.is_active:
        text = i18n.get("package_not_found", lang)
        if edit:
            await message.edit_text(text, reply_markup=get_main_menu_keyboard(lang))
        else:
            await message.answer(text, reply_markup=get_main_menu_keyboard(lang))
        return
    
    # Получаем каналы пакета
    channels = await PackageCRUD.get_package_channels(session, package_id)
    
    # Получаем ценовые периоды
    periods = _get_package_periods(package)
    
    # Формируем описание пакета
    name = package.name_en if lang == "en" and package.name_en else package.name_ru
    description = package.description_en if lang == "en" and package.description_en else package.description_ru
    
    emoji = package.emoji or "📦"
    
    # Список каналов
    channels_list = "\n".join([
        f"  • {ch.emoji or '📢'} {ch.name_en if lang == 'en' and ch.name_en else ch.name_ru}"
        for ch in channels
    ])
    
    # Экономия (если есть)
    savings_text = ""
    if package.discount_percent and package.discount_percent > 0:
        savings_text = f"\n💰 {i18n.get('savings', lang)}: -{package.discount_percent}%"
    
    text = i18n.get(
        "package_detail",
        lang,
        emoji=emoji,
        name=name,
        description=description or i18n.get("no_description", lang),
        channels_count=len(channels),
        channels_list=channels_list,
        savings=savings_text,
    )
    
    keyboard = get_package_detail_keyboard(package_id, periods, lang)
    
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


def _get_package_periods(package) -> List[dict]:
    """Получить доступные периоды подписки для пакета."""
    periods = []
    
    # 1 месяц
    if package.price_1_month and package.price_1_month > 0:
        periods.append({
            "months": 1,
            "price": package.price_1_month,
            "discount": 0,
        })
    
    # 3 месяца
    if package.price_3_month and package.price_3_month > 0:
        base_price = (package.price_1_month or 0) * 3
        discount = int(((base_price - package.price_3_month) / base_price * 100)) if base_price > 0 else 0
        periods.append({
            "months": 3,
            "price": package.price_3_month,
            "discount": max(0, discount),
        })
    
    # 6 месяцев
    if package.price_6_month and package.price_6_month > 0:
        base_price = (package.price_1_month or 0) * 6
        discount = int(((base_price - package.price_6_month) / base_price * 100)) if base_price > 0 else 0
        periods.append({
            "months": 6,
            "price": package.price_6_month,
            "discount": max(0, discount),
        })
    
    # 12 месяцев
    if package.price_12_month and package.price_12_month > 0:
        base_price = (package.price_1_month or 0) * 12
        discount = int(((base_price - package.price_12_month) / base_price * 100)) if base_price > 0 else 0
        periods.append({
            "months": 12,
            "price": package.price_12_month,
            "discount": max(0, discount),
        })
    
    # Навсегда
    if package.price_forever and package.price_forever > 0:
        periods.append({
            "months": 0,  # 0 = навсегда
            "price": package.price_forever,
            "discount": 0,
        })
    
    return periods


# ═══════════════════════════════════════════════════════════════════════════════
# 🔗 ПРЕВЬЮ КАНАЛА (для показа в списке)
# ═══════════════════════════════════════════════════════════════════════════════

async def get_channel_preview_text(
    channel,
    lang: str,
    i18n: I18n
) -> str:
    """Сформировать текст превью канала для списка."""
    name = channel.name_en if lang == "en" and channel.name_en else channel.name_ru
    emoji = channel.emoji or "📢"
    price = channel.price_1_month or 0
    
    price_text = f"${price}/мес" if lang == "ru" else f"${price}/mo"
    
    return f"{emoji} <b>{name}</b> — {price_text}"


async def get_package_preview_text(
    package,
    channels_count: int,
    lang: str,
    i18n: I18n
) -> str:
    """Сформировать текст превью пакета для списка."""
    name = package.name_en if lang == "en" and package.name_en else package.name_ru
    emoji = package.emoji or "📦"
    price = package.price_1_month or 0
    
    channels_text = f"{channels_count} каналов" if lang == "ru" else f"{channels_count} channels"
    price_text = f"${price}/мес" if lang == "ru" else f"${price}/mo"
    
    discount_text = ""
    if package.discount_percent and package.discount_percent > 0:
        discount_text = f" (-{package.discount_percent}%)"
    
    return f"{emoji} <b>{name}</b> ({channels_text}) — {price_text}{discount_text}"
