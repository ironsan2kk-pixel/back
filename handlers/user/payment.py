"""
═══════════════════════════════════════════════════════════════════════════════
💰 ХЕНДЛЕР ОПЛАТЫ
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging

from database.crud import (
    UserCRUD,
    PaymentCRUD,
    SubscriptionCRUD,
    ChannelCRUD,
    PackageCRUD,
    PromoCodeCRUD,
    ActivityLogCRUD,
)
from keyboards.user_kb import (
    get_payment_keyboard,
    get_payment_success_keyboard,
    get_main_menu_keyboard,
    get_promo_keyboard,
)
from states.user_states import SubscriptionState, PromoState
from utils.i18n import I18n
from config import settings

logger = logging.getLogger(__name__)

router = Router(name="payment")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 ПРОВЕРКА ОПЛАТЫ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("payment:check:"))
async def callback_check_payment(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Проверка статуса оплаты."""
    try:
        payment_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        await callback.answer("Error", show_alert=True)
        return
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Error", show_alert=True)
        return
    
    lang = user.language or "ru"
    
    # Получаем платёж
    payment = await PaymentCRUD.get_by_id(session, payment_id)
    
    if not payment or payment.user_id != user.id:
        await callback.answer(
            i18n.get("payment_not_found", lang),
            show_alert=True
        )
        return
    
    # Проверяем статус в Crypto Bot
    from services.crypto_bot import CryptoBotService
    
    try:
        crypto_service = CryptoBotService()
        invoice_status = await crypto_service.get_invoice_status(payment.invoice_id)
        
        if invoice_status.get("status") == "paid":
            # Оплата прошла!
            await _process_successful_payment(
                callback.message, session, user, payment, i18n, lang, state
            )
            await callback.answer(i18n.get("payment_success_alert", lang), show_alert=True)
        
        elif invoice_status.get("status") == "expired":
            # Инвойс истёк
            await PaymentCRUD.update_status(session, payment_id, "expired")
            await callback.answer(
                i18n.get("payment_expired", lang),
                show_alert=True
            )
            await state.clear()
            
            await callback.message.edit_text(
                i18n.get("payment_expired_text", lang),
                reply_markup=get_main_menu_keyboard(lang),
                parse_mode="HTML"
            )
        
        else:
            # Ещё не оплачено
            await callback.answer(
                i18n.get("payment_pending", lang),
                show_alert=True
            )
    
    except Exception as e:
        logger.error(f"Error checking payment: {e}")
        await callback.answer(
            i18n.get("payment_check_error", lang),
            show_alert=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ❌ ОТМЕНА ОПЛАТЫ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("payment:cancel:"))
async def callback_cancel_payment(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Отмена платежа."""
    await callback.answer()
    
    try:
        payment_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        return
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Получаем платёж
    payment = await PaymentCRUD.get_by_id(session, payment_id)
    
    if payment and payment.user_id == user.id and payment.status == "pending":
        await PaymentCRUD.update_status(session, payment_id, "cancelled")
        
        await ActivityLogCRUD.log(
            session,
            user_id=user.id,
            action="payment_cancelled",
            details={"payment_id": payment_id}
        )
    
    await state.clear()
    
    await callback.message.edit_text(
        i18n.get("payment_cancelled", lang),
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ПРИМЕНЕНИЕ ПРОМОКОДА К ПЛАТЕЖУ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("payment:promo:"))
async def callback_payment_promo(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Ввод промокода для платежа."""
    await callback.answer()
    
    try:
        payment_id = int(callback.data.split(":")[2])
    except (ValueError, IndexError):
        return
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Сохраняем payment_id в состояние
    await state.set_state(PromoState.waiting_code)
    await state.update_data(payment_id=payment_id)
    
    await callback.message.edit_text(
        i18n.get("promo_enter_for_payment", lang),
        reply_markup=get_promo_keyboard(lang),
        parse_mode="HTML"
    )


@router.message(PromoState.waiting_code)
async def process_promo_for_payment(
    message: Message,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Обработка введённого промокода для платежа."""
    user = await UserCRUD.get_by_telegram_id(session, message.from_user.id)
    if not user:
        return
    
    lang = user.language or "ru"
    promo_code = message.text.strip().upper()
    
    # Получаем данные из состояния
    data = await state.get_data()
    payment_id = data.get("payment_id")
    
    if not payment_id:
        await state.clear()
        await message.answer(
            i18n.get("error_occurred", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Получаем платёж
    payment = await PaymentCRUD.get_by_id(session, payment_id)
    if not payment or payment.user_id != user.id:
        await state.clear()
        await message.answer(
            i18n.get("payment_not_found", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Проверяем промокод
    promo = await PromoCodeCRUD.get_valid_promo(session, promo_code)
    
    if not promo:
        await message.answer(
            i18n.get("promo_invalid", lang),
            reply_markup=get_promo_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Проверяем, не использовал ли уже этот пользователь промокод
    if await PromoCodeCRUD.is_used_by_user(session, promo.id, user.id):
        await message.answer(
            i18n.get("promo_already_used", lang),
            reply_markup=get_promo_keyboard(lang),
            parse_mode="HTML"
        )
        return
    
    # Рассчитываем скидку
    discount = 0
    if promo.discount_type == "percent":
        discount = payment.amount * (promo.discount_value / 100)
    elif promo.discount_type == "fixed":
        discount = promo.discount_value
    
    # Не может быть больше суммы платежа
    discount = min(discount, payment.amount - 0.01)
    
    new_amount = payment.amount - discount
    
    # Обновляем платёж
    await PaymentCRUD.apply_promo(
        session,
        payment_id=payment_id,
        promo_code=promo_code,
        discount=discount,
        new_amount=new_amount
    )
    
    # Помечаем промокод как использованный
    await PromoCodeCRUD.mark_used(session, promo.id, user.id)
    
    # Создаём новый инвойс с новой суммой
    from services.crypto_bot import CryptoBotService
    
    try:
        crypto_service = CryptoBotService()
        invoice = await crypto_service.create_invoice(
            amount=new_amount,
            currency="USDT",
            description=f"Subscription #{payment_id} (with promo)",
            payload=str(payment_id),
        )
        
        await PaymentCRUD.update_invoice(
            session,
            payment_id=payment_id,
            invoice_id=invoice.get("invoice_id"),
            invoice_url=invoice.get("pay_url"),
        )
        
        await ActivityLogCRUD.log(
            session,
            user_id=user.id,
            action="promo_applied",
            details={
                "payment_id": payment_id,
                "promo_code": promo_code,
                "discount": discount,
            }
        )
        
        # Показываем обновлённый экран оплаты
        text = i18n.get(
            "payment_with_promo",
            lang,
            original_amount=f"${payment.amount:.2f}",
            discount=f"${discount:.2f}",
            promo_code=promo_code,
            final_amount=f"${new_amount:.2f}",
        )
        
        await message.answer(
            text,
            reply_markup=get_payment_keyboard(
                invoice_url=invoice.get("pay_url", "https://t.me/CryptoBot"),
                invoice_id=str(payment_id),
                lang=lang,
            ),
            parse_mode="HTML"
        )
        
        await state.set_state(SubscriptionState.waiting_payment)
        await state.update_data(payment_id=payment_id)
        
    except Exception as e:
        logger.error(f"Error creating new invoice: {e}")
        await message.answer(
            i18n.get("payment_error", lang),
            reply_markup=get_main_menu_keyboard(lang),
            parse_mode="HTML"
        )
        await state.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# ✅ ОБРАБОТКА УСПЕШНОЙ ОПЛАТЫ
# ═══════════════════════════════════════════════════════════════════════════════

async def _process_successful_payment(
    message: Message,
    session: AsyncSession,
    user,
    payment,
    i18n: I18n,
    lang: str,
    state: FSMContext
):
    """Обработка успешной оплаты — создание подписки."""
    
    # Обновляем статус платежа
    await PaymentCRUD.update_status(session, payment.id, "paid")
    
    months = payment.months or 1
    is_forever = months == 0
    
    # Рассчитываем дату окончания
    if is_forever:
        expires_at = None
    else:
        expires_at = datetime.utcnow() + timedelta(days=months * 30)
    
    invite_links = []
    
    if payment.payment_type == "channel":
        # Подписка на один канал
        channel = await ChannelCRUD.get_by_id(session, payment.item_id)
        
        if channel:
            # Создаём или продлеваем подписку
            subscription = await SubscriptionCRUD.create_or_extend(
                session,
                user_id=user.id,
                channel_id=channel.id,
                months=months,
                is_forever=is_forever,
                payment_id=payment.id,
            )
            
            # Генерируем инвайт-ссылку
            invite_link = await _generate_invite_link(channel)
            if invite_link:
                invite_links.append({
                    "name": channel.name_ru,
                    "link": invite_link,
                })
    
    elif payment.payment_type == "package":
        # Подписка на пакет каналов
        channels = await PackageCRUD.get_package_channels(session, payment.item_id)
        
        for channel in channels:
            # Создаём или продлеваем подписку для каждого канала
            subscription = await SubscriptionCRUD.create_or_extend(
                session,
                user_id=user.id,
                channel_id=channel.id,
                months=months,
                is_forever=is_forever,
                payment_id=payment.id,
            )
            
            # Генерируем инвайт-ссылку
            invite_link = await _generate_invite_link(channel)
            if invite_link:
                invite_links.append({
                    "name": channel.name_ru,
                    "link": invite_link,
                })
    
    elif payment.payment_type == "extend":
        # Продление существующей подписки
        channel = await ChannelCRUD.get_by_id(session, payment.item_id)
        
        if channel:
            subscription = await SubscriptionCRUD.extend(
                session,
                user_id=user.id,
                channel_id=channel.id,
                months=months,
                is_forever=is_forever,
            )
            
            invite_link = await _generate_invite_link(channel)
            if invite_link:
                invite_links.append({
                    "name": channel.name_ru,
                    "link": invite_link,
                })
    
    # Обновляем общую сумму трат пользователя
    final_amount = payment.final_amount or payment.amount
    await UserCRUD.add_spent(session, user.id, final_amount)

    # Начисляем бонус рефереру (10% от первой покупки)
    await _process_referral_bonus(session, user, final_amount, message.bot)

    # Логируем
    await ActivityLogCRUD.log(
        session,
        user_id=user.id,
        action="payment_success",
        details={
            "payment_id": payment.id,
            "amount": final_amount,
            "type": payment.payment_type,
        }
    )
    
    # Формируем сообщение об успешной оплате
    if invite_links:
        links_text = "\n".join([
            f"📢 <b>{link['name']}</b>: {link['link']}"
            for link in invite_links
        ])
        
        text = i18n.get(
            "payment_success_with_links",
            lang,
            amount=f"${payment.final_amount or payment.amount:.2f}",
            expires=expires_at.strftime("%d.%m.%Y") if expires_at else "♾️",
            links=links_text,
        )
    else:
        text = i18n.get(
            "payment_success",
            lang,
            amount=f"${payment.final_amount or payment.amount:.2f}",
            expires=expires_at.strftime("%d.%m.%Y") if expires_at else "♾️",
        )
    
    # Отправляем сообщение
    await state.clear()
    
    # Получаем первую ссылку для кнопки
    first_link = invite_links[0]["link"] if invite_links else None
    
    await message.edit_text(
        text,
        reply_markup=get_payment_success_keyboard(
            invite_link=first_link,
            lang=lang,
        ),
        parse_mode="HTML"
    )


async def _process_referral_bonus(session: AsyncSession, user, amount: float, bot):
    """
    Начисление бонуса рефереру за первую покупку приглашённого.

    - Проверяет, есть ли у пользователя реферер
    - Проверяет, является ли это первой покупкой
    - Начисляет 10% от суммы покупки рефереру
    """
    # Проверяем, есть ли реферер
    if not user.referred_by:
        return

    # Проверяем, является ли это первой покупкой (до этого total_spent был 0)
    # amount уже добавлен к total_spent, поэтому проверяем равенство
    if user.total_spent != amount:
        # Это не первая покупка
        return

    try:
        # Получаем реферера
        referrer = await UserCRUD.get_by_id(session, user.referred_by)
        if not referrer:
            return

        # Рассчитываем бонус (10%)
        bonus = amount * 0.10

        # Начисляем бонус на баланс реферера
        await UserCRUD.add_balance(session, referrer.id, bonus)

        # Логируем
        await ActivityLogCRUD.log(
            session,
            user_id=referrer.id,
            action="referral_bonus",
            details={
                "from_user_id": user.id,
                "purchase_amount": amount,
                "bonus": bonus,
            }
        )

        logger.info(f"Referral bonus ${bonus:.2f} credited to user {referrer.id}")

        # Уведомляем реферера о бонусе
        lang = referrer.language or "ru"
        referral_name = user.first_name or user.username or "Пользователь"

        if lang == "ru":
            text = (
                f"🎁 <b>Реферальный бонус!</b>\n\n"
                f"Ваш реферал <b>{referral_name}</b> совершил первую покупку "
                f"на сумму <b>${amount:.2f}</b>.\n\n"
                f"Вам начислено: <b>${bonus:.2f}</b> на баланс!\n\n"
                f"💰 Ваш текущий баланс: <b>${referrer.balance + bonus:.2f}</b>"
            )
        else:
            text = (
                f"🎁 <b>Referral Bonus!</b>\n\n"
                f"Your referral <b>{referral_name}</b> made their first purchase "
                f"for <b>${amount:.2f}</b>.\n\n"
                f"You received: <b>${bonus:.2f}</b> to your balance!\n\n"
                f"💰 Your current balance: <b>${referrer.balance + bonus:.2f}</b>"
            )

        await bot.send_message(referrer.telegram_id, text, parse_mode="HTML")

    except Exception as e:
        logger.warning(f"Failed to process referral bonus for user {user.id}: {e}")


async def _generate_invite_link(channel) -> str:
    """Генерация инвайт-ссылки для канала."""
    # Если у канала есть username — возвращаем публичную ссылку
    if channel.username:
        return f"https://t.me/{channel.username}"
    
    # Иначе нужно сгенерировать инвайт через Bot API
    # Это будет реализовано в сервисе подписок
    # Пока возвращаем сохранённую ссылку
    if channel.invite_link:
        return channel.invite_link
    
    # Генерация через бота (требует права администратора в канале)
    try:
        from bot import bot  # Импортируем инстанс бота
        
        link = await bot.create_chat_invite_link(
            chat_id=channel.telegram_id,
            member_limit=1,  # Одноразовая ссылка
            expire_date=datetime.utcnow() + timedelta(hours=24),
        )
        return link.invite_link
    except Exception as e:
        logger.error(f"Error creating invite link for channel {channel.id}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 🔔 WEBHOOK ДЛЯ CRYPTO BOT (будет вызываться из отдельного обработчика)
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_crypto_bot_webhook(
    session: AsyncSession,
    invoice_id: str,
    status: str,
    paid_amount: float = None
):
    """
    Обработка webhook от Crypto Bot.
    
    Вызывается из отдельного обработчика webhook'ов.
    """
    if status != "paid":
        return
    
    # Находим платёж по invoice_id
    payment = await PaymentCRUD.get_by_invoice_id(session, invoice_id)
    
    if not payment or payment.status != "pending":
        return
    
    # Получаем пользователя
    user = await UserCRUD.get_by_id(session, payment.user_id)
    if not user:
        return
    
    lang = user.language or "ru"
    
    # Обрабатываем успешную оплату
    # Здесь нужно будет отправить уведомление пользователю
    # Это будет реализовано в Чате 4 (интеграция с Crypto Bot)
    
    logger.info(f"Payment {payment.id} completed via webhook")
