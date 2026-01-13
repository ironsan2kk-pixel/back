"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ХЕНДЛЕР /START И ВЫБОР ЯЗЫКА
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from database.crud import UserCRUD, ActivityLogCRUD
from keyboards.user_kb import get_language_keyboard, get_main_menu_keyboard
from utils.i18n import I18n

logger = logging.getLogger(__name__)

router = Router(name="start")


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 КОМАНДА /START
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """
    Обработчик команды /start.
    
    - Если пользователь новый → показываем выбор языка
    - Если пользователь существует → показываем главное меню
    """
    await state.clear()
    
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Проверяем deep link (реферальная ссылка или промокод)
    deep_link = None
    if message.text and len(message.text.split()) > 1:
        deep_link = message.text.split()[1]
    
    # Получаем или создаём пользователя
    user = await UserCRUD.get_by_telegram_id(session, user_id)
    
    if user is None:
        # Новый пользователь
        # Парсим реферальную ссылку
        referred_by = None
        if deep_link:
            referred_by = await _parse_referral(session, deep_link)

        user = await UserCRUD.create(
            session,
            telegram_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            referred_by=referred_by
        )

        # Уведомляем реферера о новом приглашённом
        if referred_by:
            await _notify_referrer(session, referred_by, user, message.bot)
        
        # Логируем активность
        await ActivityLogCRUD.log(
            session,
            user_id=user.id,
            action="start",
            details={"deep_link": deep_link, "is_new": True}
        )
        
        logger.info(f"New user registered: {user_id} (@{username})")
        
        # Показываем выбор языка для нового пользователя
        welcome_text = (
            "🌐 <b>Выберите язык / Choose your language</b>\n\n"
            "🇷🇺 Русский — нажмите кнопку ниже\n"
            "🇬🇧 English — press the button below"
        )
        
        await message.answer(
            welcome_text,
            reply_markup=get_language_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Существующий пользователь
    await UserCRUD.update_activity(session, user.id)
    
    # Логируем активность
    await ActivityLogCRUD.log(
        session,
        user_id=user.id,
        action="start",
        details={"deep_link": deep_link, "is_new": False}
    )
    
    # Обрабатываем deep link если есть
    if deep_link:
        await _handle_deep_link(message, session, user, deep_link, i18n)
        return
    
    # Показываем главное меню
    lang = user.language or "ru"
    welcome_text = i18n.get("welcome_back", lang, name=first_name or "Друг")
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 ВЫБОР ЯЗЫКА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("lang:"))
async def callback_select_language(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state: FSMContext
):
    """Обработчик выбора языка."""
    await callback.answer()
    
    lang = callback.data.split(":")[1]  # ru или en
    user_id = callback.from_user.id
    first_name = callback.from_user.first_name
    
    # Обновляем язык пользователя
    user = await UserCRUD.get_by_telegram_id(session, user_id)
    if user:
        await UserCRUD.update_language(session, user.id, lang)
        
        # Логируем
        await ActivityLogCRUD.log(
            session,
            user_id=user.id,
            action="language_change",
            details={"language": lang}
        )
    
    # Отправляем приветственное сообщение на выбранном языке
    welcome_text = i18n.get("welcome_new", lang, name=first_name or "Друг")
    
    await callback.message.edit_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "menu:language")
async def callback_change_language(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n
):
    """Обработчик смены языка из меню."""
    await callback.answer()
    
    user = await UserCRUD.get_by_telegram_id(session, callback.from_user.id)
    lang = user.language if user else "ru"
    
    text = i18n.get("select_language", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_language_keyboard(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 КОМАНДА /HELP
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("help"))
async def cmd_help(
    message: Message,
    session: AsyncSession,
    i18n: I18n
):
    """Обработчик команды /help."""
    user = await UserCRUD.get_by_telegram_id(session, message.from_user.id)
    lang = user.language if user else "ru"
    
    help_text = i18n.get("help_text", lang)
    
    await message.answer(
        help_text,
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

async def _parse_referral(session: AsyncSession, deep_link: str) -> Optional[int]:
    """Парсит реферальную ссылку и возвращает ID пригласившего пользователя."""
    if deep_link.startswith("ref_"):
        referral_code = deep_link.replace("ref_", "")
        # Ищем пользователя по реферальному коду
        referrer = await UserCRUD.get_by_referral_code(session, referral_code)
        if referrer:
            return referrer.id
    return None


async def _notify_referrer(session: AsyncSession, referrer_id: int, new_user, bot):
    """Уведомляет реферера о новом приглашённом пользователе."""
    try:
        referrer = await UserCRUD.get_by_id(session, referrer_id)
        if not referrer:
            return

        lang = referrer.language or "ru"
        new_user_name = new_user.first_name or new_user.username or "Пользователь"

        if lang == "ru":
            text = (
                f"🎉 <b>Новый реферал!</b>\n\n"
                f"Пользователь <b>{new_user_name}</b> зарегистрировался по вашей ссылке.\n\n"
                f"Вы получите бонус, когда он совершит первую покупку!"
            )
        else:
            text = (
                f"🎉 <b>New Referral!</b>\n\n"
                f"User <b>{new_user_name}</b> registered using your link.\n\n"
                f"You'll receive a bonus when they make their first purchase!"
            )

        await bot.send_message(referrer.telegram_id, text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to notify referrer {referrer_id}: {e}")


async def _handle_deep_link(
    message: Message,
    session: AsyncSession,
    user,
    deep_link: str,
    i18n: I18n
):
    """Обрабатывает deep link."""
    lang = user.language or "ru"
    first_name = message.from_user.first_name
    
    # Обработка промокода через deep link
    if deep_link.startswith("promo_"):
        promo_code = deep_link.replace("promo_", "")
        from handlers.user.promo import apply_promo_code
        await apply_promo_code(message, session, user, promo_code, i18n)
        return
    
    # Обработка прямой ссылки на канал
    if deep_link.startswith("channel_"):
        try:
            channel_id = int(deep_link.replace("channel_", ""))
            from handlers.user.catalog import show_channel_detail
            await show_channel_detail(message, session, channel_id, i18n, lang)
            return
        except ValueError:
            pass
    
    # Обработка прямой ссылки на пакет
    if deep_link.startswith("package_"):
        try:
            package_id = int(deep_link.replace("package_", ""))
            from handlers.user.catalog import show_package_detail
            await show_package_detail(message, session, package_id, i18n, lang)
            return
        except ValueError:
            pass
    
    # Неизвестный deep link — показываем главное меню
    welcome_text = i18n.get("welcome_back", lang, name=first_name or "Друг")
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(lang),
        parse_mode="HTML"
    )
