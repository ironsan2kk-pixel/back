"""
═══════════════════════════════════════════════════════════════════════════════
🏠 ХЕНДЛЕР ГЛАВНОГО МЕНЮ
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database.crud import UserCRUD, ChannelCRUD, PackageCRUD
from keyboards.user_kb import (
    get_main_menu_keyboard,
    get_catalog_keyboard,
    get_packages_keyboard,
    get_profile_keyboard,
    get_promo_keyboard,
    get_support_keyboard,
)
from states.user_states import PromoState
from utils.i18n import I18n
from config import settings

logger = logging.getLogger(__name__)

router = Router(name="menu")


# ═══════════════════════════════════════════════════════════════════════════════
# 🏠 ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("menu"))
async def cmd_menu(
    message: Message,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Команда /menu — показать главное меню."""
    await state.clear()
    
    user = await UserCRUD.get_by_telegram_id(session, message.from_user.id)
    lang = user.language if user else "ru"
    
    text = i18n.get("main_menu", lang)
    
    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "menu:back")
async def callback_back_to_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Возврат в главное меню."""
    await callback.answer()
    await state.clear()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    text = i18n.get("main_menu", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 КАТАЛОГ КАНАЛОВ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "menu:catalog")
async def callback_catalog(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Открыть каталог каналов."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    # Получаем активные каналы
    channels = await ChannelCRUD.get_all_active(session)
    
    if not channels:
        text = i18n.get("catalog_empty", lang)
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Преобразуем в список словарей для клавиатуры
    channels_data = [
        {
            "id": ch.id,
            "name_ru": ch.name_ru,
            "name_en": ch.name_en,
            "emoji": ch.emoji or "📢",
            "price_1_month": ch.price_1_month,
        }
        for ch in channels
    ]
    
    text = i18n.get("catalog_title", lang, count=len(channels))
    
    await callback.message.edit_text(
        text,
        reply_markup=get_catalog_keyboard(channels_data, lang, page=0),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("catalog:page:"))
async def callback_catalog_page(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Пагинация каталога каналов."""
    page_str = callback.data.split(":")[2]
    
    if page_str == "current":
        await callback.answer()
        return
    
    page = int(page_str)
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    channels = await ChannelCRUD.get_all_active(session)
    channels_data = [
        {
            "id": ch.id,
            "name_ru": ch.name_ru,
            "name_en": ch.name_en,
            "emoji": ch.emoji or "📢",
            "price_1_month": ch.price_1_month,
        }
        for ch in channels
    ]
    
    text = i18n.get("catalog_title", lang, count=len(channels))
    
    await callback.message.edit_text(
        text,
        reply_markup=get_catalog_keyboard(channels_data, lang, page=page),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ПАКЕТЫ ПОДПИСОК
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "menu:packages")
async def callback_packages(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Открыть список пакетов подписок."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    # Получаем активные пакеты
    packages = await PackageCRUD.get_all_active(session)
    
    if not packages:
        text = i18n.get("packages_empty", lang)
        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Преобразуем в список словарей для клавиатуры
    packages_data = []
    for pkg in packages:
        # Получаем количество каналов в пакете
        channels_count = await PackageCRUD.get_channels_count(session, pkg.id)
        
        packages_data.append({
            "id": pkg.id,
            "name_ru": pkg.name_ru,
            "name_en": pkg.name_en,
            "emoji": pkg.emoji or "📦",
            "price": pkg.price_1_month,
            "channels_count": channels_count,
        })
    
    text = i18n.get("packages_title", lang, count=len(packages))
    
    await callback.message.edit_text(
        text,
        reply_markup=get_packages_keyboard(packages_data, lang, page=0),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("packages:page:"))
async def callback_packages_page(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Пагинация пакетов."""
    page_str = callback.data.split(":")[2]
    
    if page_str == "current":
        await callback.answer()
        return
    
    page = int(page_str)
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    packages = await PackageCRUD.get_all_active(session)
    packages_data = []
    for pkg in packages:
        channels_count = await PackageCRUD.get_channels_count(session, pkg.id)
        packages_data.append({
            "id": pkg.id,
            "name_ru": pkg.name_ru,
            "name_en": pkg.name_en,
            "emoji": pkg.emoji or "📦",
            "price": pkg.price_1_month,
            "channels_count": channels_count,
        })
    
    text = i18n.get("packages_title", lang, count=len(packages))
    
    await callback.message.edit_text(
        text,
        reply_markup=get_packages_keyboard(packages_data, lang, page=page),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 👤 ПРОФИЛЬ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "menu:profile")
async def callback_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Открыть профиль пользователя."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Получаем подписки пользователя
    from database.crud import SubscriptionCRUD
    subscriptions = await SubscriptionCRUD.get_user_active_subscriptions(session, user.id)
    
    # Статистика
    total_spent = await UserCRUD.get_total_spent(session, user.id)
    subscriptions_count = len(subscriptions)
    
    text = i18n.get(
        "profile_info",
        lang,
        user_id=user.telegram_id,
        username=user.username or "-",
        name=user.first_name or "-",
        language="🇷🇺 Русский" if lang == "ru" else "🇬🇧 English",
        subscriptions_count=subscriptions_count,
        total_spent=f"${total_spent:.2f}",
        registered=user.created_at.strftime("%d.%m.%Y"),
    )
    
    # Преобразуем подписки в список словарей
    subs_data = [
        {
            "id": sub.id,
            "channel_name": sub.channel.name_ru if lang == "ru" else (sub.channel.name_en or sub.channel.name_ru),
            "expires_at": sub.expires_at,
            "is_forever": sub.is_forever,
        }
        for sub in subscriptions
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=get_profile_keyboard(subs_data, lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ПРОМОКОД
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "menu:promo")
async def callback_promo(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Открыть ввод промокода."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    text = i18n.get("promo_enter", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promo_keyboard(lang),
        parse_mode="HTML"
    )
    
    # Устанавливаем состояние ожидания промокода
    await state.set_state(PromoState.waiting_code)


# ═══════════════════════════════════════════════════════════════════════════════
# 💬 ПОДДЕРЖКА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "menu:support")
async def callback_support(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Открыть меню поддержки."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    text = i18n.get("support_text", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_support_keyboard(settings.SUPPORT_USERNAME, lang),
        parse_mode="HTML"
    )
