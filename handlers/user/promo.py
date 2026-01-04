"""
═══════════════════════════════════════════════════════════════════════════════
🎟️ ХЕНДЛЕР ПРОМОКОДОВ
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
    PromoCodeCRUD,
    SubscriptionCRUD,
    ChannelCRUD,
    ActivityLogCRUD,
)
from keyboards.user_kb import (
    get_promo_keyboard,
    get_promo_result_keyboard,
    get_main_menu_keyboard,
)
from states.user_states import PromoState
from utils.i18n import I18n

logger = logging.getLogger(__name__)

router = Router(name="promo")


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ КОМАНДА /PROMO
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("promo"))
async def cmd_promo(
    message: Message,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Команда /promo — ввод промокода."""
    user = await UserCRUD.get_by_telegram_id(session, message.from_user.id)
    lang = user.language if user else "ru"
    
    # Проверяем, есть ли код в команде
    parts = message.text.split()
    if len(parts) > 1:
        # Есть код — сразу проверяем
        promo_code = parts[1].strip().upper()
        await apply_promo_code(message, session, user, promo_code, i18n)
        return
    
    # Нет кода — просим ввести
    await state.set_state(PromoState.waiting_code)
    
    await message.answer(
        i18n.get("promo_enter", lang),
        reply_markup=get_promo_keyboard(lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 📝 ВВОД ПРОМОКОДА
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(PromoState.waiting_code)
async def process_promo_input(
    message: Message,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Обработка введённого промокода."""
    # Проверяем, что это не команда
    if message.text.startswith("/"):
        await state.clear()
        return
    
    user = await UserCRUD.get_by_telegram_id(session, message.from_user.id)
    if not user:
        return
    
    promo_code = message.text.strip().upper()
    
    await state.clear()
    await apply_promo_code(message, session, user, promo_code, i18n)


# ═══════════════════════════════════════════════════════════════════════════════
# ✅ ПРИМЕНЕНИЕ ПРОМОКОДА
# ═══════════════════════════════════════════════════════════════════════════════

async def apply_promo_code(
    message: Message,
    session: AsyncSession,
    user,
    promo_code: str,
    i18n: I18n
):
    """
    Применение промокода.
    
    Промокоды могут давать:
    - Скидку на следующую покупку
    - Бесплатный доступ к каналу на определённый срок
    - Бонусное время к подписке
    """
    lang = user.language or "ru"
    
    # Получаем промокод
    promo = await PromoCodeCRUD.get_valid_promo(session, promo_code)
    
    if not promo:
        await message.answer(
            i18n.get("promo_invalid", lang),
            reply_markup=get_promo_result_keyboard(success=False, lang=lang),
            parse_mode="HTML"
        )
        return
    
    # Проверяем, не использовал ли уже этот пользователь промокод
    if await PromoCodeCRUD.is_used_by_user(session, promo.id, user.id):
        await message.answer(
            i18n.get("promo_already_used", lang),
            reply_markup=get_promo_result_keyboard(success=False, lang=lang),
            parse_mode="HTML"
        )
        return
    
    # Проверяем лимит использований
    if promo.max_uses and promo.uses_count >= promo.max_uses:
        await message.answer(
            i18n.get("promo_limit_reached", lang),
            reply_markup=get_promo_result_keyboard(success=False, lang=lang),
            parse_mode="HTML"
        )
        return
    
    # Проверяем срок действия
    if promo.valid_until and promo.valid_until < datetime.utcnow():
        await message.answer(
            i18n.get("promo_expired", lang),
            reply_markup=get_promo_result_keyboard(success=False, lang=lang),
            parse_mode="HTML"
        )
        return
    
    # Обрабатываем в зависимости от типа промокода
    if promo.promo_type == "free_access":
        # Бесплатный доступ к каналу
        await _apply_free_access_promo(message, session, user, promo, i18n, lang)
    
    elif promo.promo_type == "discount":
        # Скидка — сохраняем для следующей покупки
        await _apply_discount_promo(message, session, user, promo, i18n, lang)
    
    elif promo.promo_type == "bonus_time":
        # Бонусное время к существующей подписке
        await _apply_bonus_time_promo(message, session, user, promo, i18n, lang)
    
    else:
        # Неизвестный тип — применяем как скидку
        await _apply_discount_promo(message, session, user, promo, i18n, lang)


# ═══════════════════════════════════════════════════════════════════════════════
# 🆓 ПРОМОКОД: БЕСПЛАТНЫЙ ДОСТУП
# ═══════════════════════════════════════════════════════════════════════════════

async def _apply_free_access_promo(
    message: Message,
    session: AsyncSession,
    user,
    promo,
    i18n: I18n,
    lang: str
):
    """Применение промокода на бесплатный доступ."""
    
    # Получаем канал
    channel_id = promo.channel_id
    if not channel_id:
        # Если канал не указан — даём доступ к первому активному
        channels = await ChannelCRUD.get_all_active(session)
        if not channels:
            await message.answer(
                i18n.get("no_channels_available", lang),
                reply_markup=get_promo_result_keyboard(success=False, lang=lang),
                parse_mode="HTML"
            )
            return
        channel_id = channels[0].id
    
    channel = await ChannelCRUD.get_by_id(session, channel_id)
    if not channel:
        await message.answer(
            i18n.get("channel_not_found", lang),
            reply_markup=get_promo_result_keyboard(success=False, lang=lang),
            parse_mode="HTML"
        )
        return
    
    # Срок действия бесплатного доступа
    days = promo.free_days or 7  # По умолчанию 7 дней
    
    # Создаём подписку
    subscription = await SubscriptionCRUD.create_or_extend(
        session,
        user_id=user.id,
        channel_id=channel_id,
        months=0,  # Указываем дни, а не месяцы
        days=days,
        is_forever=False,
        promo_id=promo.id,
    )
    
    # Помечаем промокод как использованный
    await PromoCodeCRUD.mark_used(session, promo.id, user.id)
    
    # Логируем
    await ActivityLogCRUD.log(
        session,
        user_id=user.id,
        action="promo_free_access",
        details={
            "promo_code": promo.code,
            "channel_id": channel_id,
            "days": days,
        }
    )
    
    # Генерируем инвайт-ссылку
    from handlers.user.payment import _generate_invite_link
    invite_link = await _generate_invite_link(channel)
    
    channel_name = channel.name_en if lang == "en" and channel.name_en else channel.name_ru
    
    text = i18n.get(
        "promo_free_access_success",
        lang,
        promo_code=promo.code,
        channel_name=channel_name,
        days=days,
        invite_link=invite_link or "—",
    )
    
    from keyboards.user_kb import get_payment_success_keyboard
    
    await message.answer(
        text,
        reply_markup=get_payment_success_keyboard(invite_link=invite_link, lang=lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 💰 ПРОМОКОД: СКИДКА
# ═══════════════════════════════════════════════════════════════════════════════

async def _apply_discount_promo(
    message: Message,
    session: AsyncSession,
    user,
    promo,
    i18n: I18n,
    lang: str
):
    """Применение промокода на скидку."""
    
    # Сохраняем промокод для пользователя
    await UserCRUD.save_promo(session, user.id, promo.code)
    
    # Помечаем промокод как использованный (резервируем)
    # Фактическое использование произойдёт при оплате
    
    # Формируем текст скидки
    if promo.discount_type == "percent":
        discount_text = f"{promo.discount_value}%"
    else:
        discount_text = f"${promo.discount_value}"
    
    # Логируем
    await ActivityLogCRUD.log(
        session,
        user_id=user.id,
        action="promo_discount_saved",
        details={
            "promo_code": promo.code,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
        }
    )
    
    text = i18n.get(
        "promo_discount_success",
        lang,
        promo_code=promo.code,
        discount=discount_text,
    )
    
    await message.answer(
        text,
        reply_markup=get_promo_result_keyboard(success=True, lang=lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ⏰ ПРОМОКОД: БОНУСНОЕ ВРЕМЯ
# ═══════════════════════════════════════════════════════════════════════════════

async def _apply_bonus_time_promo(
    message: Message,
    session: AsyncSession,
    user,
    promo,
    i18n: I18n,
    lang: str
):
    """Применение промокода на бонусное время."""
    
    # Получаем активные подписки пользователя
    subscriptions = await SubscriptionCRUD.get_user_active_subscriptions(session, user.id)
    
    if not subscriptions:
        await message.answer(
            i18n.get("promo_no_subscriptions", lang),
            reply_markup=get_promo_result_keyboard(success=False, lang=lang),
            parse_mode="HTML"
        )
        return
    
    # Добавляем бонусное время ко всем активным подпискам
    bonus_days = promo.bonus_days or 7
    extended_channels = []
    
    for subscription in subscriptions:
        if not subscription.is_forever:
            await SubscriptionCRUD.add_bonus_days(session, subscription.id, bonus_days)
            
            channel = subscription.channel
            channel_name = channel.name_en if lang == "en" and channel.name_en else channel.name_ru
            extended_channels.append(channel_name)
    
    if not extended_channels:
        await message.answer(
            i18n.get("promo_no_extendable_subscriptions", lang),
            reply_markup=get_promo_result_keyboard(success=False, lang=lang),
            parse_mode="HTML"
        )
        return
    
    # Помечаем промокод как использованный
    await PromoCodeCRUD.mark_used(session, promo.id, user.id)
    
    # Логируем
    await ActivityLogCRUD.log(
        session,
        user_id=user.id,
        action="promo_bonus_time",
        details={
            "promo_code": promo.code,
            "bonus_days": bonus_days,
            "channels": extended_channels,
        }
    )
    
    channels_text = "\n".join([f"  • {ch}" for ch in extended_channels])
    
    text = i18n.get(
        "promo_bonus_time_success",
        lang,
        promo_code=promo.code,
        bonus_days=bonus_days,
        channels=channels_text,
    )
    
    await message.answer(
        text,
        reply_markup=get_promo_result_keyboard(success=True, lang=lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ПРОВЕРКА ПРОМОКОДА (без применения)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("checkpromo"))
async def cmd_check_promo(
    message: Message,
    session: AsyncSession,
    i18n: I18n
):
    """Команда /checkpromo — проверка промокода без применения."""
    user = await UserCRUD.get_by_telegram_id(session, message.from_user.id)
    lang = user.language if user else "ru"
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            i18n.get("promo_check_usage", lang),
            parse_mode="HTML"
        )
        return
    
    promo_code = parts[1].strip().upper()
    
    # Получаем промокод
    promo = await PromoCodeCRUD.get_by_code(session, promo_code)
    
    if not promo:
        await message.answer(
            i18n.get("promo_not_found", lang),
            parse_mode="HTML"
        )
        return
    
    # Проверяем статус
    is_valid = True
    status_notes = []
    
    if not promo.is_active:
        is_valid = False
        status_notes.append(i18n.get("promo_status_inactive", lang))
    
    if promo.valid_until and promo.valid_until < datetime.utcnow():
        is_valid = False
        status_notes.append(i18n.get("promo_status_expired", lang))
    
    if promo.max_uses and promo.uses_count >= promo.max_uses:
        is_valid = False
        status_notes.append(i18n.get("promo_status_limit_reached", lang))
    
    if user and await PromoCodeCRUD.is_used_by_user(session, promo.id, user.id):
        is_valid = False
        status_notes.append(i18n.get("promo_status_already_used", lang))
    
    # Формируем информацию о промокоде
    promo_type_names = {
        "ru": {
            "free_access": "🆓 Бесплатный доступ",
            "discount": "💰 Скидка",
            "bonus_time": "⏰ Бонусное время",
        },
        "en": {
            "free_access": "🆓 Free Access",
            "discount": "💰 Discount",
            "bonus_time": "⏰ Bonus Time",
        }
    }
    
    promo_type_text = promo_type_names[lang].get(
        promo.promo_type,
        promo.promo_type
    )
    
    # Детали промокода
    details = []
    
    if promo.promo_type == "discount":
        if promo.discount_type == "percent":
            details.append(f"📊 {i18n.get('discount', lang)}: {promo.discount_value}%")
        else:
            details.append(f"📊 {i18n.get('discount', lang)}: ${promo.discount_value}")
    
    elif promo.promo_type == "free_access":
        details.append(f"📅 {i18n.get('duration', lang)}: {promo.free_days or 7} {i18n.get('days', lang)}")
    
    elif promo.promo_type == "bonus_time":
        details.append(f"📅 {i18n.get('bonus', lang)}: +{promo.bonus_days or 7} {i18n.get('days', lang)}")
    
    if promo.valid_until:
        details.append(f"⏰ {i18n.get('valid_until', lang)}: {promo.valid_until.strftime('%d.%m.%Y')}")
    
    if promo.max_uses:
        details.append(f"📈 {i18n.get('uses', lang)}: {promo.uses_count}/{promo.max_uses}")
    
    status_emoji = "✅" if is_valid else "❌"
    status_text = i18n.get("promo_valid", lang) if is_valid else i18n.get("promo_invalid_status", lang)
    
    notes_text = "\n".join(status_notes) if status_notes else ""
    details_text = "\n".join(details) if details else ""
    
    text = i18n.get(
        "promo_check_result",
        lang,
        code=promo.code,
        type=promo_type_text,
        status_emoji=status_emoji,
        status=status_text,
        details=details_text,
        notes=notes_text,
    )
    
    await message.answer(text, parse_mode="HTML")
