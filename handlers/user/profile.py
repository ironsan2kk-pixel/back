"""
═══════════════════════════════════════════════════════════════════════════════
👤 ХЕНДЛЕР ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from database.crud import (
    UserCRUD,
    SubscriptionCRUD,
    PaymentCRUD,
    ActivityLogCRUD,
)
from keyboards.user_kb import (
    get_profile_keyboard,
    get_subscriptions_keyboard,
    get_purchase_history_keyboard,
    get_main_menu_keyboard,
    get_back_button,
)
from utils.i18n import I18n

logger = logging.getLogger(__name__)

router = Router(name="profile")


# ═══════════════════════════════════════════════════════════════════════════════
# 👤 КОМАНДА /PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("profile"))
async def cmd_profile(
    message: Message,
    session: AsyncSession,
    i18n: I18n
):
    """Команда /profile — профиль пользователя."""
    user = await UserCRUD.get_by_telegram_id(session, message.from_user.id)
    
    if not user:
        # Создаём пользователя если его нет
        user = await UserCRUD.create(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
    
    lang = user.language or "ru"
    
    await _show_profile(message, session, user, i18n, lang)


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 МОИ ПОДПИСКИ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "profile:subscriptions")
async def callback_subscriptions(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Показать список подписок пользователя."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Получаем активные подписки
    subscriptions = await SubscriptionCRUD.get_user_active_subscriptions(session, user.id)
    
    if not subscriptions:
        text = i18n.get("no_subscriptions", lang)
        await callback.message.edit_text(
            text,
            reply_markup=get_back_button("menu:profile", lang),
            parse_mode="HTML"
        )
        return
    
    # Формируем список подписок
    subs_list = []
    for sub in subscriptions:
        channel = sub.channel
        channel_name = channel.name_en if lang == "en" and channel.name_en else channel.name_ru
        emoji = channel.emoji or "📢"
        
        if sub.is_forever:
            expires_text = "♾️ " + i18n.get("forever", lang)
            status = "✅"
        else:
            days_left = (sub.expires_at - datetime.utcnow()).days
            
            if days_left < 0:
                status = "❌"
                expires_text = i18n.get("expired", lang)
            elif days_left <= 3:
                status = "⚠️"
                expires_text = f"{days_left} " + i18n.get("days_left", lang)
            else:
                status = "✅"
                expires_text = sub.expires_at.strftime("%d.%m.%Y")
        
        subs_list.append({
            "id": sub.id,
            "channel_name": channel_name,
            "emoji": emoji,
            "expires_text": expires_text,
            "status": status,
            "expires_at": sub.expires_at,
            "is_forever": sub.is_forever,
        })
    
    # Формируем текст
    text = i18n.get("subscriptions_title", lang, count=len(subs_list))
    
    for sub in subs_list:
        text += f"\n\n{sub['status']} {sub['emoji']} <b>{sub['channel_name']}</b>"
        text += f"\n   └ {sub['expires_text']}"
    
    # Клавиатура со списком подписок
    subs_data = [
        {
            "id": sub["id"],
            "channel_name": sub["channel_name"],
            "expires_at": sub["expires_at"],
            "is_forever": sub["is_forever"],
        }
        for sub in subs_list
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=get_subscriptions_keyboard(subs_data, lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 📜 ИСТОРИЯ ПОКУПОК
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "profile:history")
async def callback_purchase_history(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Показать историю покупок."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    await _show_purchase_history(callback.message, session, user, i18n, lang, page=0)


@router.callback_query(F.data.startswith("history:page:"))
async def callback_history_page(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Пагинация истории покупок."""
    page_str = callback.data.split(":")[2]
    
    if page_str == "current":
        await callback.answer()
        return
    
    page = int(page_str)
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    await _show_purchase_history(callback.message, session, user, i18n, lang, page=page)


async def _show_purchase_history(
    message: Message,
    session: AsyncSession,
    user,
    i18n: I18n,
    lang: str,
    page: int = 0
):
    """Показать страницу истории покупок."""
    per_page = 10
    
    # Получаем все оплаченные платежи пользователя
    payments = await PaymentCRUD.get_user_payments(session, user.id, status="paid")
    
    if not payments:
        text = i18n.get("no_purchases", lang)
        await message.edit_text(
            text,
            reply_markup=get_back_button("menu:profile", lang),
            parse_mode="HTML"
        )
        return
    
    # Пагинация
    total_pages = (len(payments) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_payments = payments[start_idx:end_idx]
    
    # Формируем текст
    text = i18n.get("purchase_history_title", lang, count=len(payments))
    
    for payment in page_payments:
        date = payment.created_at.strftime("%d.%m.%Y")
        amount = payment.final_amount or payment.amount
        
        # Тип покупки
        if payment.payment_type == "channel":
            type_emoji = "📢"
        elif payment.payment_type == "package":
            type_emoji = "📦"
        else:
            type_emoji = "🔄"
        
        # Статус
        status_emoji = "✅" if payment.status == "paid" else "⏳"
        
        text += f"\n\n{status_emoji} <code>{date}</code>"
        text += f"\n   {type_emoji} ${amount:.2f}"
        
        if payment.promo_code:
            text += f" (🎟️ {payment.promo_code})"
    
    # Клавиатура
    purchases_data = [{"id": p.id} for p in payments]
    
    await message.edit_text(
        text,
        reply_markup=get_purchase_history_keyboard(purchases_data, lang, page=page, per_page=per_page),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 ПРОДЛЕНИЕ ПОДПИСКИ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "profile:extend")
async def callback_extend_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Меню продления подписок."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Получаем подписки, которые можно продлить
    subscriptions = await SubscriptionCRUD.get_user_active_subscriptions(session, user.id)
    
    # Фильтруем — исключаем вечные подписки
    extendable = [sub for sub in subscriptions if not sub.is_forever]
    
    if not extendable:
        text = i18n.get("no_extendable_subscriptions", lang)
        await callback.message.edit_text(
            text,
            reply_markup=get_back_button("menu:profile", lang),
            parse_mode="HTML"
        )
        return
    
    # Формируем список для продления
    subs_data = [
        {
            "id": sub.id,
            "channel_name": sub.channel.name_en if lang == "en" and sub.channel.name_en else sub.channel.name_ru,
            "expires_at": sub.expires_at,
            "is_forever": False,
        }
        for sub in extendable
    ]
    
    text = i18n.get("select_subscription_to_extend", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_subscriptions_keyboard(subs_data, lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sub:extend:"))
async def callback_extend_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Продление конкретной подписки."""
    await callback.answer()
    
    try:
        subscription_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
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
    
    # Перенаправляем на страницу канала для выбора периода
    from handlers.user.catalog import show_channel_detail
    await show_channel_detail(callback.message, session, subscription.channel_id, i18n, lang, edit=True)


@router.callback_query(F.data.startswith("sub:view:"))
async def callback_view_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Просмотр детальной информации о подписке."""
    await callback.answer()
    
    try:
        subscription_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
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
    channel_name = channel.name_en if lang == "en" and channel.name_en else channel.name_ru
    emoji = channel.emoji or "📢"
    
    # Формируем детальную информацию
    if subscription.is_forever:
        expires_text = "♾️ " + i18n.get("forever", lang)
        status = "✅ " + i18n.get("active", lang)
    else:
        days_left = (subscription.expires_at - datetime.utcnow()).days
        
        if days_left < 0:
            status = "❌ " + i18n.get("expired", lang)
            expires_text = subscription.expires_at.strftime("%d.%m.%Y")
        elif days_left <= 3:
            status = "⚠️ " + i18n.get("expiring_soon", lang)
            expires_text = f"{subscription.expires_at.strftime('%d.%m.%Y')} ({days_left} {i18n.get('days_left', lang)})"
        else:
            status = "✅ " + i18n.get("active", lang)
            expires_text = f"{subscription.expires_at.strftime('%d.%m.%Y')} ({days_left} {i18n.get('days_left', lang)})"
    
    # Дата начала
    started = subscription.created_at.strftime("%d.%m.%Y")
    
    text = i18n.get(
        "subscription_detail",
        lang,
        emoji=emoji,
        channel_name=channel_name,
        status=status,
        started=started,
        expires=expires_text,
    )
    
    # Кнопки
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    # Кнопка перехода в канал
    if channel.username:
        builder.row(InlineKeyboardButton(
            text=f"📢 {i18n.get('go_to_channel', lang)}",
            url=f"https://t.me/{channel.username}"
        ))
    elif channel.invite_link:
        builder.row(InlineKeyboardButton(
            text=f"📢 {i18n.get('go_to_channel', lang)}",
            url=channel.invite_link
        ))
    
    # Кнопка продления (если не вечная подписка)
    if not subscription.is_forever:
        builder.row(InlineKeyboardButton(
            text=f"🔄 {i18n.get('extend', lang)}",
            callback_data=f"sub:extend:{subscription_id}"
        ))
    
    # Кнопка назад
    builder.row(InlineKeyboardButton(
        text=f"◀️ {i18n.get('back', lang)}",
        callback_data="profile:subscriptions"
    ))
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 👥 РЕФЕРАЛЬНАЯ ПРОГРАММА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "profile:referrals")
async def callback_referrals(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Показать реферальную программу."""
    await callback.answer()

    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return

    lang = user.language or "ru"
    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username

    # Генерируем реферальную ссылку
    referral_link = f"https://t.me/{bot_username}?start=ref_{user.referral_code}"

    # Получаем статистику рефералов
    stats = await UserCRUD.get_referral_stats(session, user.id)

    # Получаем баланс пользователя
    balance = user.balance or 0.0

    if lang == "ru":
        text = (
            f"👥 <b>Реферальная программа</b>\n\n"
            f"Приглашайте друзей и получайте <b>10%</b> от их первой покупки!\n\n"
            f"💰 <b>Ваш баланс:</b> <b>${balance:.2f}</b>\n\n"
            f"📊 <b>Ваша статистика:</b>\n"
            f"├ Приглашено: <b>{stats['total_referrals']}</b> чел.\n"
            f"├ С покупками: <b>{stats['referrals_with_purchases']}</b> чел.\n"
            f"└ Потрачено рефералами: <b>${stats['total_referral_spending']:.2f}</b>\n\n"
            f"🔗 <b>Ваша реферальная ссылка:</b>\n"
            f"<code>{referral_link}</code>\n\n"
            f"👆 Нажмите на ссылку, чтобы скопировать"
        )
    else:
        text = (
            f"👥 <b>Referral Program</b>\n\n"
            f"Invite friends and get <b>10%</b> of their first purchase!\n\n"
            f"💰 <b>Your Balance:</b> <b>${balance:.2f}</b>\n\n"
            f"📊 <b>Your Statistics:</b>\n"
            f"├ Invited: <b>{stats['total_referrals']}</b> people\n"
            f"├ With purchases: <b>{stats['referrals_with_purchases']}</b> people\n"
            f"└ Referrals spent: <b>${stats['total_referral_spending']:.2f}</b>\n\n"
            f"🔗 <b>Your referral link:</b>\n"
            f"<code>{referral_link}</code>\n\n"
            f"👆 Tap the link to copy"
        )

    # Клавиатура
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()

    # Кнопка "Поделиться"
    share_text = "Привет! Присоединяйся к нашему боту:" if lang == "ru" else "Hi! Join our bot:"
    share_url = f"https://t.me/share/url?url={referral_link}&text={share_text}"
    builder.row(InlineKeyboardButton(
        text="📤 Поделиться" if lang == "ru" else "📤 Share",
        url=share_url
    ))

    # Кнопка "Мои рефералы" если есть рефералы
    if stats['total_referrals'] > 0:
        builder.row(InlineKeyboardButton(
            text="👥 Мои рефералы" if lang == "ru" else "👥 My Referrals",
            callback_data="profile:referrals:list"
        ))

    # Кнопка назад
    builder.row(InlineKeyboardButton(
        text="◀️ Назад" if lang == "ru" else "◀️ Back",
        callback_data="menu:profile"
    ))

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "profile:referrals:list")
async def callback_referrals_list(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Показать список рефералов."""
    await callback.answer()

    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return

    lang = user.language or "ru"

    # Получаем список рефералов
    referrals = await UserCRUD.get_referrals(session, user.id, limit=20)

    if not referrals:
        text = "У вас пока нет рефералов." if lang == "ru" else "You don't have any referrals yet."
        await callback.message.edit_text(
            text,
            reply_markup=get_back_button("profile:referrals", lang),
            parse_mode="HTML"
        )
        return

    if lang == "ru":
        text = f"👥 <b>Ваши рефералы ({len(referrals)}):</b>\n\n"
    else:
        text = f"👥 <b>Your Referrals ({len(referrals)}):</b>\n\n"

    for i, ref in enumerate(referrals, 1):
        name = ref.first_name or ref.username or "Пользователь"
        date = ref.created_at.strftime("%d.%m.%Y")
        spent = ref.total_spent

        status = "💰" if spent > 0 else "⏳"
        text += f"{i}. {status} <b>{name}</b>\n"
        text += f"   └ {date}"
        if spent > 0:
            text += f" • ${spent:.2f}"
        text += "\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_back_button("profile:referrals", lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

async def _show_profile(
    message: Message,
    session: AsyncSession,
    user,
    i18n: I18n,
    lang: str,
    edit: bool = False
):
    """Показать профиль пользователя."""
    
    # Получаем статистику
    subscriptions = await SubscriptionCRUD.get_user_active_subscriptions(session, user.id)
    total_spent = await UserCRUD.get_total_spent(session, user.id)
    
    # Формируем текст профиля
    text = i18n.get(
        "profile_info",
        lang,
        user_id=user.telegram_id,
        username=user.username or "-",
        name=user.first_name or "-",
        language="🇷🇺 Русский" if lang == "ru" else "🇬🇧 English",
        subscriptions_count=len(subscriptions),
        total_spent=f"${total_spent:.2f}",
        registered=user.created_at.strftime("%d.%m.%Y"),
    )
    
    # Данные подписок для клавиатуры
    subs_data = [
        {
            "id": sub.id,
            "channel_name": sub.channel.name_ru,
            "expires_at": sub.expires_at,
            "is_forever": sub.is_forever,
        }
        for sub in subscriptions
    ]
    
    if edit:
        await message.edit_text(
            text,
            reply_markup=get_profile_keyboard(subs_data, lang),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text,
            reply_markup=get_profile_keyboard(subs_data, lang),
            parse_mode="HTML"
        )
