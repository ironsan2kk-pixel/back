"""
═══════════════════════════════════════════════════════════════════════════════
💳 ХЕНДЛЕР ПОДПИСКИ И ОФОРМЛЕНИЯ ЗАКАЗА
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
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
    PromoCodeCRUD,
    ActivityLogCRUD,
)
from keyboards.user_kb import (
    get_payment_keyboard,
    get_confirm_keyboard,
    get_main_menu_keyboard,
    get_back_button,
)
from states.user_states import SubscriptionState
from utils.i18n import I18n
from config import settings

logger = logging.getLogger(__name__)

router = Router(name="subscription")


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 ПОДПИСКА НА КАНАЛ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("subscribe:"))
async def callback_subscribe_channel(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Начать оформление подписки на канал."""
    await callback.answer()
    
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    
    try:
        channel_id = int(parts[1])
        months = int(parts[2])
    except ValueError:
        return
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Получаем канал
    channel = await ChannelCRUD.get_by_id(session, channel_id)
    if not channel or not channel.is_active:
        await callback.message.edit_text(
            i18n.get("channel_not_found", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Проверяем, нет ли уже активной подписки
    existing_sub = await SubscriptionCRUD.get_user_channel_subscription(
        session, user.id, channel_id
    )
    if existing_sub and existing_sub.is_active:
        # Предлагаем продлить
        await _show_extend_subscription(
            callback.message, session, user, existing_sub, months, i18n, lang
        )
        return
    
    # Получаем цену
    price = _get_channel_price(channel, months)
    if price is None or price <= 0:
        await callback.message.edit_text(
            i18n.get("price_not_available", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Сохраняем данные в состояние
    await state.set_state(SubscriptionState.confirming)
    await state.update_data(
        subscription_type="channel",
        item_id=channel_id,
        months=months,
        base_price=price,
        final_price=price,
        promo_code=None,
        discount=0,
    )
    
    # Показываем подтверждение
    await _show_subscription_confirm(
        callback.message,
        session,
        user,
        i18n,
        lang,
        item_type="channel",
        item=channel,
        months=months,
        price=price,
    )


@router.callback_query(F.data.startswith("subscribe_package:"))
async def callback_subscribe_package(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Начать оформление подписки на пакет."""
    await callback.answer()
    
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    
    try:
        package_id = int(parts[1])
        months = int(parts[2])
    except ValueError:
        return
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Получаем пакет
    package = await PackageCRUD.get_by_id(session, package_id)
    if not package or not package.is_active:
        await callback.message.edit_text(
            i18n.get("package_not_found", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Получаем цену
    price = _get_package_price(package, months)
    if price is None or price <= 0:
        await callback.message.edit_text(
            i18n.get("price_not_available", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Получаем каналы пакета
    channels = await PackageCRUD.get_package_channels(session, package_id)
    
    # Сохраняем данные в состояние
    await state.set_state(SubscriptionState.confirming)
    await state.update_data(
        subscription_type="package",
        item_id=package_id,
        months=months,
        base_price=price,
        final_price=price,
        promo_code=None,
        discount=0,
        channel_ids=[ch.id for ch in channels],
    )
    
    # Показываем подтверждение
    await _show_subscription_confirm(
        callback.message,
        session,
        user,
        i18n,
        lang,
        item_type="package",
        item=package,
        months=months,
        price=price,
        channels=channels,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ✅ ПОДТВЕРЖДЕНИЕ ПОДПИСКИ
# ═══════════════════════════════════════════════════════════════════════════════

async def _show_subscription_confirm(
    message: Message,
    session: AsyncSession,
    user,
    i18n: I18n,
    lang: str,
    item_type: str,
    item,
    months: int,
    price: float,
    channels: list = None,
    promo_code: str = None,
    discount: float = 0,
):
    """Показать экран подтверждения подписки."""
    
    # Название
    name = item.name_en if lang == "en" and item.name_en else item.name_ru
    emoji = item.emoji or ("📢" if item_type == "channel" else "📦")
    
    # Период
    period_names = {
        "ru": {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев", 0: "Навсегда"},
        "en": {1: "1 month", 3: "3 months", 6: "6 months", 12: "12 months", 0: "Forever"},
    }
    period_text = period_names[lang].get(months, f"{months} мес." if lang == "ru" else f"{months} mo.")
    
    # Итоговая цена
    final_price = price
    if discount > 0:
        final_price = price - discount
    
    # Дата окончания
    if months == 0:
        expires_text = "♾️ " + (i18n.get("forever", lang))
    else:
        expires_date = datetime.utcnow() + timedelta(days=months * 30)
        expires_text = expires_date.strftime("%d.%m.%Y")
    
    # Список каналов (для пакета)
    channels_text = ""
    if channels:
        channels_list = "\n".join([
            f"  • {ch.emoji or '📢'} {ch.name_en if lang == 'en' and ch.name_en else ch.name_ru}"
            for ch in channels
        ])
        channels_text = f"\n\n📋 {i18n.get('included_channels', lang)}:\n{channels_list}"
    
    # Промокод
    promo_text = ""
    if promo_code and discount > 0:
        promo_text = f"\n🎟️ {i18n.get('promo_applied', lang)}: {promo_code} (-${discount:.2f})"
    
    # Формируем текст
    text = i18n.get(
        "subscription_confirm",
        lang,
        emoji=emoji,
        name=name,
        period=period_text,
        base_price=f"${price:.2f}",
        final_price=f"${final_price:.2f}",
        expires=expires_text,
        channels=channels_text,
        promo=promo_text,
    )
    
    # Клавиатура
    keyboard = get_confirm_keyboard(
        confirm_callback="subscription:confirm",
        cancel_callback="subscription:cancel",
        lang=lang
    )
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "subscription:confirm", SubscriptionState.confirming)
async def callback_confirm_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Подтверждение подписки — создание платежа."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Получаем данные из состояния
    data = await state.get_data()
    
    subscription_type = data.get("subscription_type")
    item_id = data.get("item_id")
    months = data.get("months", 1)
    final_price = data.get("final_price", 0)
    promo_code = data.get("promo_code")
    channel_ids = data.get("channel_ids", [])
    
    if not subscription_type or not item_id or final_price <= 0:
        await callback.message.edit_text(
            i18n.get("error_occurred", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Создаём платёж в базе
    payment = await PaymentCRUD.create(
        session,
        user_id=user.id,
        amount=final_price,
        currency="USDT",
        payment_type=subscription_type,
        item_id=item_id,
        months=months,
        promo_code=promo_code,
        channel_ids=channel_ids if subscription_type == "package" else None,
    )
    
    # Создаём инвойс в Crypto Bot (будет реализовано в Чате 4)
    # Пока создаём заглушку
    from services.crypto_bot import CryptoBotService
    
    try:
        crypto_service = CryptoBotService()
        invoice = await crypto_service.create_invoice(
            amount=final_price,
            currency="USDT",
            description=f"Subscription #{payment.id}",
            payload=str(payment.id),
        )
        
        # Обновляем платёж с данными инвойса
        await PaymentCRUD.update_invoice(
            session,
            payment_id=payment.id,
            invoice_id=invoice.get("invoice_id"),
            invoice_url=invoice.get("pay_url"),
        )
        
        # Логируем
        await ActivityLogCRUD.log(
            session,
            user_id=user.id,
            action="payment_created",
            details={
                "payment_id": payment.id,
                "amount": final_price,
                "type": subscription_type,
            }
        )
        
        # Переключаем состояние
        await state.set_state(SubscriptionState.waiting_payment)
        await state.update_data(payment_id=payment.id)
        
        # Показываем кнопку оплаты
        text = i18n.get(
            "payment_created",
            lang,
            amount=f"${final_price:.2f}",
            invoice_id=invoice.get("invoice_id", "N/A"),
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_payment_keyboard(
                invoice_url=invoice.get("pay_url", "https://t.me/CryptoBot"),
                invoice_id=str(payment.id),
                lang=lang,
            ),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        
        await callback.message.edit_text(
            i18n.get("payment_error", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        await state.clear()


@router.callback_query(F.data == "subscription:cancel")
async def callback_cancel_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Отмена оформления подписки."""
    await callback.answer()
    await state.clear()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    text = i18n.get("subscription_cancelled", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 ПРОДЛЕНИЕ ПОДПИСКИ
# ═══════════════════════════════════════════════════════════════════════════════

async def _show_extend_subscription(
    message: Message,
    session: AsyncSession,
    user,
    subscription,
    months: int,
    i18n: I18n,
    lang: str,
):
    """Показать диалог продления подписки."""
    channel = subscription.channel
    
    name = channel.name_en if lang == "en" and channel.name_en else channel.name_ru
    emoji = channel.emoji or "📢"
    
    # Текущая дата окончания
    if subscription.is_forever:
        current_expires = "♾️ " + i18n.get("forever", lang)
    else:
        current_expires = subscription.expires_at.strftime("%d.%m.%Y")
    
    # Новая дата окончания
    if months == 0:
        new_expires = "♾️ " + i18n.get("forever", lang)
    else:
        base_date = subscription.expires_at if not subscription.is_forever else datetime.utcnow()
        new_expires_date = base_date + timedelta(days=months * 30)
        new_expires = new_expires_date.strftime("%d.%m.%Y")
    
    # Цена
    price = _get_channel_price(channel, months)
    
    text = i18n.get(
        "extend_subscription",
        lang,
        emoji=emoji,
        name=name,
        current_expires=current_expires,
        new_expires=new_expires,
        price=f"${price:.2f}",
    )
    
    keyboard = get_confirm_keyboard(
        confirm_callback=f"extend:{subscription.id}:{months}",
        cancel_callback="menu:catalog",
        lang=lang
    )
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("extend:"))
async def callback_extend_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Подтверждение продления подписки."""
    await callback.answer()
    
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    
    try:
        subscription_id = int(parts[1])
        months = int(parts[2])
    except ValueError:
        return
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Получаем подписку
    subscription = await SubscriptionCRUD.get_by_id(session, subscription_id)
    if not subscription or subscription.user_id != user.id:
        await callback.message.edit_text(
            i18n.get("subscription_not_found", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    channel = subscription.channel
    price = _get_channel_price(channel, months)
    
    # Сохраняем данные для оплаты
    await state.set_state(SubscriptionState.confirming)
    await state.update_data(
        subscription_type="extend",
        item_id=channel.id,
        subscription_id=subscription_id,
        months=months,
        base_price=price,
        final_price=price,
        promo_code=None,
        discount=0,
    )
    
    # Перенаправляем на подтверждение
    await callback_confirm_subscription(callback, session, i18n, state)


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def _get_channel_price(channel, months: int) -> Optional[float]:
    """Получить цену канала для указанного периода."""
    price_map = {
        1: channel.price_1_month,
        3: channel.price_3_month,
        6: channel.price_6_month,
        12: channel.price_12_month,
        0: channel.price_forever,  # 0 = навсегда
    }
    return price_map.get(months)


def _get_package_price(package, months: int) -> Optional[float]:
    """Получить цену пакета для указанного периода."""
    price_map = {
        1: package.price_1_month,
        3: package.price_3_month,
        6: package.price_6_month,
        12: package.price_12_month,
        0: package.price_forever,  # 0 = навсегда
    }
    return price_map.get(months)
