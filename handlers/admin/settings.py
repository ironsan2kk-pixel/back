"""
Административный модуль: Настройки бота
Чат 5.2 - Telegram бот продажи доступов к каналам

Функционал:
- Общие настройки бота
- Настройки оплаты
- Настройки уведомлений
- Управление администраторами
- Тексты и локализация
- Резервное копирование
"""

from datetime import datetime
from typing import Optional
import json
import os

from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, 
    Message,
    BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    SettingsCRUD, AdminCRUD, UserCRUD,
    ChannelCRUD, PackageCRUD, SubscriptionCRUD,
    PaymentCRUD, PromoCRUD
)
from keyboards.admin_kb import (
    get_settings_menu_kb,
    get_settings_general_kb,
    get_settings_payment_kb,
    get_settings_notifications_kb,
    get_settings_admins_kb,
    get_settings_texts_kb,
    get_settings_backup_kb,
    get_confirm_kb,
    get_back_to_settings_kb
)
from states.admin_states import SettingsAdminState
from utils.i18n import get_text

router = Router()


# ==================== ГЛАВНОЕ МЕНЮ НАСТРОЕК ====================

@router.callback_query(F.data == "admin:settings")
async def show_settings_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Главное меню настроек.
    """
    await state.clear()
    lang = callback.from_user.language_code or "ru"
    
    settings_crud = SettingsCRUD(session)
    
    # Получаем текущие настройки
    bot_name = await settings_crud.get("bot_name", "Subscription Bot")
    maintenance_mode = await settings_crud.get("maintenance_mode", "false")
    
    text = get_text("admin_settings_menu", lang).format(
        bot_name=bot_name,
        maintenance="🔴 ВКЛ" if maintenance_mode == "true" else "🟢 ВЫКЛ"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu_kb(lang)
    )
    await callback.answer()


# ==================== ОБЩИЕ НАСТРОЙКИ ====================

@router.callback_query(F.data == "admin:settings:general")
async def show_general_settings(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Общие настройки бота.
    """
    lang = callback.from_user.language_code or "ru"
    
    settings_crud = SettingsCRUD(session)
    
    # Текущие значения
    bot_name = await settings_crud.get("bot_name", "Subscription Bot")
    welcome_message = await settings_crud.get("welcome_message", "Добро пожаловать!")
    support_username = await settings_crud.get("support_username", "")
    maintenance_mode = await settings_crud.get("maintenance_mode", "false")
    default_language = await settings_crud.get("default_language", "ru")
    
    text = get_text("admin_settings_general", lang).format(
        bot_name=bot_name,
        welcome_message=welcome_message[:100] + "..." if len(welcome_message) > 100 else welcome_message,
        support_username=support_username or "Не указан",
        maintenance="🔴 Включён" if maintenance_mode == "true" else "🟢 Выключен",
        default_language=default_language.upper()
    )
    
    await state.set_state(SettingsAdminState.viewing_general)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_general_kb(lang, maintenance_mode == "true")
    )
    await callback.answer()


@router.callback_query(
    SettingsAdminState.viewing_general,
    F.data == "admin:settings:edit:bot_name"
)
async def edit_bot_name(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Редактирование названия бота.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.editing_bot_name)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_bot_name", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:general")
    )
    await callback.answer()


@router.message(SettingsAdminState.editing_bot_name)
async def save_bot_name(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Сохранение названия бота.
    """
    lang = message.from_user.language_code or "ru"
    
    bot_name = message.text.strip()
    
    if len(bot_name) < 2 or len(bot_name) > 64:
        await message.answer(
            get_text("admin_settings_bot_name_invalid", lang)
        )
        return
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("bot_name", bot_name)
    
    await message.answer(
        get_text("admin_settings_bot_name_saved", lang).format(name=bot_name)
    )
    
    await state.set_state(SettingsAdminState.viewing_general)


@router.callback_query(
    SettingsAdminState.viewing_general,
    F.data == "admin:settings:edit:welcome"
)
async def edit_welcome_message(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Редактирование приветственного сообщения.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.editing_welcome)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_welcome", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:general")
    )
    await callback.answer()


@router.message(SettingsAdminState.editing_welcome)
async def save_welcome_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Сохранение приветственного сообщения.
    """
    lang = message.from_user.language_code or "ru"
    
    welcome = message.text.strip()
    
    if len(welcome) > 4000:
        await message.answer(
            get_text("admin_settings_welcome_too_long", lang)
        )
        return
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("welcome_message", welcome)
    
    await message.answer(
        get_text("admin_settings_welcome_saved", lang)
    )
    
    await state.set_state(SettingsAdminState.viewing_general)


@router.callback_query(
    SettingsAdminState.viewing_general,
    F.data == "admin:settings:edit:support"
)
async def edit_support_username(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Редактирование username поддержки.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.editing_support)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_support", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:general")
    )
    await callback.answer()


@router.message(SettingsAdminState.editing_support)
async def save_support_username(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Сохранение username поддержки.
    """
    lang = message.from_user.language_code or "ru"
    
    support = message.text.strip().replace("@", "")
    
    if len(support) < 5 or len(support) > 32:
        await message.answer(
            get_text("admin_settings_support_invalid", lang)
        )
        return
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("support_username", support)
    
    await message.answer(
        get_text("admin_settings_support_saved", lang).format(username=support)
    )
    
    await state.set_state(SettingsAdminState.viewing_general)


@router.callback_query(
    SettingsAdminState.viewing_general,
    F.data == "admin:settings:toggle:maintenance"
)
async def toggle_maintenance_mode(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Переключение режима обслуживания.
    """
    lang = callback.from_user.language_code or "ru"
    
    settings_crud = SettingsCRUD(session)
    current = await settings_crud.get("maintenance_mode", "false")
    
    new_value = "false" if current == "true" else "true"
    await settings_crud.set("maintenance_mode", new_value)
    
    await callback.answer(
        get_text("admin_settings_maintenance_toggled", lang).format(
            status="включён" if new_value == "true" else "выключен"
        ),
        show_alert=True
    )
    
    # Обновляем меню
    await show_general_settings(callback, session, state)


@router.callback_query(
    SettingsAdminState.viewing_general,
    F.data.startswith("admin:settings:lang:")
)
async def change_default_language(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Изменение языка по умолчанию.
    """
    lang_code = callback.data.split(":")[-1]
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("default_language", lang_code)
    
    await callback.answer(f"Язык по умолчанию: {lang_code.upper()}")
    await show_general_settings(callback, session, state)


# ==================== НАСТРОЙКИ ОПЛАТЫ ====================

@router.callback_query(F.data == "admin:settings:payment")
async def show_payment_settings(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Настройки оплаты.
    """
    lang = callback.from_user.language_code or "ru"
    
    settings_crud = SettingsCRUD(session)
    
    # Текущие значения
    crypto_bot_token = await settings_crud.get("crypto_bot_token", "")
    payment_currency = await settings_crud.get("payment_currency", "USDT")
    payment_timeout = await settings_crud.get("payment_timeout", "3600")
    min_amount = await settings_crud.get("min_payment_amount", "1")
    
    # Маскируем токен
    masked_token = "••••" + crypto_bot_token[-8:] if len(crypto_bot_token) > 8 else "Не указан"
    
    text = get_text("admin_settings_payment", lang).format(
        crypto_bot_token=masked_token,
        currency=payment_currency,
        timeout=int(payment_timeout) // 60,
        min_amount=min_amount
    )
    
    await state.set_state(SettingsAdminState.viewing_payment)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_payment_kb(lang)
    )
    await callback.answer()


@router.callback_query(
    SettingsAdminState.viewing_payment,
    F.data == "admin:settings:edit:crypto_token"
)
async def edit_crypto_token(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Редактирование токена Crypto Bot.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.editing_crypto_token)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_crypto_token", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:payment")
    )
    await callback.answer()


@router.message(SettingsAdminState.editing_crypto_token)
async def save_crypto_token(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Сохранение токена Crypto Bot.
    """
    lang = message.from_user.language_code or "ru"
    
    token = message.text.strip()
    
    # Удаляем сообщение с токеном для безопасности
    try:
        await message.delete()
    except:
        pass
    
    if len(token) < 10:
        await message.answer(
            get_text("admin_settings_crypto_token_invalid", lang)
        )
        return
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("crypto_bot_token", token)
    
    await message.answer(
        get_text("admin_settings_crypto_token_saved", lang)
    )
    
    await state.set_state(SettingsAdminState.viewing_payment)


@router.callback_query(
    SettingsAdminState.viewing_payment,
    F.data.startswith("admin:settings:currency:")
)
async def change_payment_currency(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Изменение валюты оплаты.
    """
    currency = callback.data.split(":")[-1]
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("payment_currency", currency)
    
    await callback.answer(f"Валюта: {currency}")
    await show_payment_settings(callback, session, state)


@router.callback_query(
    SettingsAdminState.viewing_payment,
    F.data == "admin:settings:edit:timeout"
)
async def edit_payment_timeout(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Редактирование таймаута оплаты.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.editing_timeout)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_timeout", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:payment")
    )
    await callback.answer()


@router.message(SettingsAdminState.editing_timeout)
async def save_payment_timeout(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Сохранение таймаута оплаты.
    """
    lang = message.from_user.language_code or "ru"
    
    try:
        minutes = int(message.text.strip())
        if minutes < 5 or minutes > 1440:
            raise ValueError
    except ValueError:
        await message.answer(
            get_text("admin_settings_timeout_invalid", lang)
        )
        return
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("payment_timeout", str(minutes * 60))
    
    await message.answer(
        get_text("admin_settings_timeout_saved", lang).format(minutes=minutes)
    )
    
    await state.set_state(SettingsAdminState.viewing_payment)


# ==================== НАСТРОЙКИ УВЕДОМЛЕНИЙ ====================

@router.callback_query(F.data == "admin:settings:notifications")
async def show_notification_settings(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Настройки уведомлений.
    """
    lang = callback.from_user.language_code or "ru"
    
    settings_crud = SettingsCRUD(session)
    
    # Текущие значения
    notify_new_user = await settings_crud.get("notify_new_user", "true")
    notify_new_payment = await settings_crud.get("notify_new_payment", "true")
    notify_subscription_end = await settings_crud.get("notify_subscription_end", "true")
    notify_days_before = await settings_crud.get("notify_days_before", "3")
    admin_chat_id = await settings_crud.get("admin_notifications_chat", "")
    
    text = get_text("admin_settings_notifications", lang).format(
        notify_new_user="✅" if notify_new_user == "true" else "❌",
        notify_new_payment="✅" if notify_new_payment == "true" else "❌",
        notify_subscription_end="✅" if notify_subscription_end == "true" else "❌",
        notify_days_before=notify_days_before,
        admin_chat_id=admin_chat_id or "Не указан"
    )
    
    await state.set_state(SettingsAdminState.viewing_notifications)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_notifications_kb(
            lang,
            notify_new_user == "true",
            notify_new_payment == "true",
            notify_subscription_end == "true"
        )
    )
    await callback.answer()


@router.callback_query(
    SettingsAdminState.viewing_notifications,
    F.data.startswith("admin:settings:toggle:notify_")
)
async def toggle_notification(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Переключение уведомления.
    """
    setting_name = callback.data.replace("admin:settings:toggle:", "")
    
    settings_crud = SettingsCRUD(session)
    current = await settings_crud.get(setting_name, "true")
    
    new_value = "false" if current == "true" else "true"
    await settings_crud.set(setting_name, new_value)
    
    await callback.answer("✅" if new_value == "true" else "❌")
    await show_notification_settings(callback, session, state)


@router.callback_query(
    SettingsAdminState.viewing_notifications,
    F.data == "admin:settings:edit:notify_days"
)
async def edit_notify_days(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Редактирование дней до уведомления.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.editing_notify_days)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_notify_days", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:notifications")
    )
    await callback.answer()


@router.message(SettingsAdminState.editing_notify_days)
async def save_notify_days(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Сохранение дней до уведомления.
    """
    lang = message.from_user.language_code or "ru"
    
    try:
        days = int(message.text.strip())
        if days < 1 or days > 30:
            raise ValueError
    except ValueError:
        await message.answer(
            get_text("admin_settings_notify_days_invalid", lang)
        )
        return
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("notify_days_before", str(days))
    
    await message.answer(
        get_text("admin_settings_notify_days_saved", lang).format(days=days)
    )
    
    await state.set_state(SettingsAdminState.viewing_notifications)


@router.callback_query(
    SettingsAdminState.viewing_notifications,
    F.data == "admin:settings:edit:admin_chat"
)
async def edit_admin_chat(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Редактирование чата для уведомлений админов.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.editing_admin_chat)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_admin_chat", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:notifications")
    )
    await callback.answer()


@router.message(SettingsAdminState.editing_admin_chat)
async def save_admin_chat(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Сохранение чата для уведомлений админов.
    """
    lang = message.from_user.language_code or "ru"
    
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            get_text("admin_settings_admin_chat_invalid", lang)
        )
        return
    
    settings_crud = SettingsCRUD(session)
    await settings_crud.set("admin_notifications_chat", str(chat_id))
    
    await message.answer(
        get_text("admin_settings_admin_chat_saved", lang).format(chat_id=chat_id)
    )
    
    await state.set_state(SettingsAdminState.viewing_notifications)


# ==================== УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ ====================

@router.callback_query(F.data == "admin:settings:admins")
async def show_admins_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Список администраторов.
    """
    lang = callback.from_user.language_code or "ru"
    
    admin_crud = AdminCRUD(session)
    admins = await admin_crud.get_all()
    
    if not admins:
        text = get_text("admin_settings_no_admins", lang)
    else:
        items = []
        for admin in admins:
            role_emoji = "👑" if admin.is_superadmin else "👤"
            items.append(
                f"{role_emoji} {admin.telegram_id} | @{admin.username or 'нет'} | "
                f"{admin.full_name or 'Без имени'}"
            )
        
        text = get_text("admin_settings_admins_list", lang).format(
            count=len(admins),
            admins="\n".join(items)
        )
    
    await state.set_state(SettingsAdminState.viewing_admins)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_admins_kb(lang)
    )
    await callback.answer()


@router.callback_query(
    SettingsAdminState.viewing_admins,
    F.data == "admin:settings:add_admin"
)
async def add_admin_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Начало добавления администратора.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.adding_admin)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_admin_id", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:admins")
    )
    await callback.answer()


@router.message(SettingsAdminState.adding_admin)
async def add_admin_process(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Добавление администратора.
    """
    lang = message.from_user.language_code or "ru"
    
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            get_text("admin_settings_admin_id_invalid", lang)
        )
        return
    
    admin_crud = AdminCRUD(session)
    
    # Проверяем, не существует ли уже
    existing = await admin_crud.get_by_telegram_id(telegram_id)
    if existing:
        await message.answer(
            get_text("admin_settings_admin_exists", lang)
        )
        return
    
    # Добавляем
    await admin_crud.create(telegram_id=telegram_id)
    
    await message.answer(
        get_text("admin_settings_admin_added", lang).format(id=telegram_id)
    )
    
    await state.set_state(SettingsAdminState.viewing_admins)


@router.callback_query(
    SettingsAdminState.viewing_admins,
    F.data == "admin:settings:remove_admin"
)
async def remove_admin_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Начало удаления администратора.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.removing_admin)
    
    await callback.message.edit_text(
        get_text("admin_settings_enter_admin_id_remove", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:admins")
    )
    await callback.answer()


@router.message(SettingsAdminState.removing_admin)
async def remove_admin_process(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Удаление администратора.
    """
    lang = message.from_user.language_code or "ru"
    
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            get_text("admin_settings_admin_id_invalid", lang)
        )
        return
    
    # Нельзя удалить самого себя
    if telegram_id == message.from_user.id:
        await message.answer(
            get_text("admin_settings_cannot_remove_self", lang)
        )
        return
    
    admin_crud = AdminCRUD(session)
    
    # Проверяем существование
    admin = await admin_crud.get_by_telegram_id(telegram_id)
    if not admin:
        await message.answer(
            get_text("admin_settings_admin_not_found", lang)
        )
        return
    
    # Нельзя удалить суперадмина
    if admin.is_superadmin:
        await message.answer(
            get_text("admin_settings_cannot_remove_superadmin", lang)
        )
        return
    
    # Удаляем
    await admin_crud.delete(telegram_id)
    
    await message.answer(
        get_text("admin_settings_admin_removed", lang).format(id=telegram_id)
    )
    
    await state.set_state(SettingsAdminState.viewing_admins)


# ==================== РЕЗЕРВНОЕ КОПИРОВАНИЕ ====================

@router.callback_query(F.data == "admin:settings:backup")
async def show_backup_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Меню резервного копирования.
    """
    lang = callback.from_user.language_code or "ru"
    
    text = get_text("admin_settings_backup_menu", lang)
    
    await state.set_state(SettingsAdminState.viewing_backup)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_backup_kb(lang)
    )
    await callback.answer()


@router.callback_query(
    SettingsAdminState.viewing_backup,
    F.data == "admin:settings:backup:create"
)
async def create_backup(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Создание резервной копии.
    """
    lang = callback.from_user.language_code or "ru"
    
    await callback.answer(get_text("admin_backup_creating", lang))
    
    # Собираем все данные
    user_crud = UserCRUD(session)
    channel_crud = ChannelCRUD(session)
    package_crud = PackageCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    payment_crud = PaymentCRUD(session)
    promo_crud = PromoCRUD(session)
    settings_crud = SettingsCRUD(session)
    admin_crud = AdminCRUD(session)
    
    backup_data = {
        "created_at": datetime.utcnow().isoformat(),
        "version": "1.0",
        "users": [],
        "channels": [],
        "packages": [],
        "subscriptions": [],
        "payments": [],
        "promos": [],
        "settings": [],
        "admins": []
    }
    
    # Пользователи
    users = await user_crud.get_all()
    for u in users:
        backup_data["users"].append({
            "id": u.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "full_name": u.full_name,
            "language_code": u.language_code,
            "is_banned": u.is_banned,
            "created_at": u.created_at.isoformat()
        })
    
    # Каналы
    channels = await channel_crud.get_all()
    for c in channels:
        backup_data["channels"].append({
            "id": c.id,
            "telegram_id": c.telegram_id,
            "name": c.name,
            "description": c.description,
            "is_active": c.is_active,
            "price_30": str(c.price_30) if c.price_30 else None,
            "price_90": str(c.price_90) if c.price_90 else None,
            "price_365": str(c.price_365) if c.price_365 else None,
            "created_at": c.created_at.isoformat()
        })
    
    # Пакеты
    packages = await package_crud.get_all()
    for p in packages:
        backup_data["packages"].append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "is_active": p.is_active,
            "price_30": str(p.price_30) if p.price_30 else None,
            "price_90": str(p.price_90) if p.price_90 else None,
            "price_365": str(p.price_365) if p.price_365 else None,
            "created_at": p.created_at.isoformat()
        })
    
    # Подписки
    subscriptions = await subscription_crud.get_all()
    for s in subscriptions:
        backup_data["subscriptions"].append({
            "id": s.id,
            "user_id": s.user_id,
            "channel_id": s.channel_id,
            "package_id": s.package_id,
            "is_active": s.is_active,
            "start_date": s.start_date.isoformat(),
            "end_date": s.end_date.isoformat(),
            "is_renewal": s.is_renewal,
            "created_at": s.created_at.isoformat()
        })
    
    # Платежи
    payments = await payment_crud.get_all()
    for pay in payments:
        backup_data["payments"].append({
            "id": pay.id,
            "user_id": pay.user_id,
            "amount": str(pay.amount) if pay.amount else None,
            "currency": pay.currency,
            "status": pay.status,
            "invoice_id": pay.invoice_id,
            "channel_id": pay.channel_id,
            "package_id": pay.package_id,
            "duration_days": pay.duration_days,
            "created_at": pay.created_at.isoformat()
        })
    
    # Промокоды
    promos = await promo_crud.get_all()
    for pr in promos:
        backup_data["promos"].append({
            "id": pr.id,
            "code": pr.code,
            "discount_type": pr.discount_type,
            "discount_value": str(pr.discount_value) if pr.discount_value else None,
            "usage_limit": pr.usage_limit,
            "times_used": pr.times_used,
            "is_active": pr.is_active,
            "expires_at": pr.expires_at.isoformat() if pr.expires_at else None,
            "created_at": pr.created_at.isoformat()
        })
    
    # Настройки
    settings = await settings_crud.get_all()
    for s in settings:
        backup_data["settings"].append({
            "key": s.key,
            "value": s.value
        })
    
    # Админы
    admins = await admin_crud.get_all()
    for a in admins:
        backup_data["admins"].append({
            "telegram_id": a.telegram_id,
            "username": a.username,
            "full_name": a.full_name,
            "is_superadmin": a.is_superadmin
        })
    
    # Создаём JSON файл
    json_data = json.dumps(backup_data, ensure_ascii=False, indent=2)
    file_bytes = json_data.encode('utf-8')
    
    filename = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    await callback.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption=get_text("admin_backup_created", lang).format(
            users=len(backup_data["users"]),
            channels=len(backup_data["channels"]),
            packages=len(backup_data["packages"]),
            subscriptions=len(backup_data["subscriptions"]),
            payments=len(backup_data["payments"])
        )
    )


@router.callback_query(
    SettingsAdminState.viewing_backup,
    F.data == "admin:settings:backup:restore"
)
async def restore_backup_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Начало восстановления из резервной копии.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(SettingsAdminState.restoring_backup)
    
    await callback.message.edit_text(
        get_text("admin_backup_upload_file", lang),
        reply_markup=get_back_to_settings_kb(lang, "admin:settings:backup")
    )
    await callback.answer()


@router.message(
    SettingsAdminState.restoring_backup,
    F.document
)
async def restore_backup_process(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot
):
    """
    Восстановление из резервной копии.
    """
    lang = message.from_user.language_code or "ru"
    
    if not message.document.file_name.endswith('.json'):
        await message.answer(
            get_text("admin_backup_invalid_file", lang)
        )
        return
    
    # Скачиваем файл
    file = await bot.get_file(message.document.file_id)
    file_data = await bot.download_file(file.file_path)
    
    try:
        backup_data = json.loads(file_data.read().decode('utf-8'))
    except json.JSONDecodeError:
        await message.answer(
            get_text("admin_backup_invalid_json", lang)
        )
        return
    
    # Подтверждение
    await state.update_data(backup_data=backup_data)
    await state.set_state(SettingsAdminState.confirming_restore)
    
    await message.answer(
        get_text("admin_backup_confirm_restore", lang).format(
            created_at=backup_data.get("created_at", "Unknown"),
            users=len(backup_data.get("users", [])),
            channels=len(backup_data.get("channels", [])),
            subscriptions=len(backup_data.get("subscriptions", []))
        ),
        reply_markup=get_confirm_kb(lang)
    )


@router.callback_query(
    SettingsAdminState.confirming_restore,
    F.data == "admin:confirm"
)
async def restore_backup_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Подтверждение восстановления.
    """
    lang = callback.from_user.language_code or "ru"
    data = await state.get_data()
    backup_data = data.get("backup_data", {})
    
    await callback.answer(get_text("admin_backup_restoring", lang))
    
    # TODO: Реализовать восстановление данных
    # Это требует очистки существующих данных и вставки новых
    # Рекомендуется выполнять это через миграцию или отдельный скрипт
    
    await state.clear()
    
    await callback.message.edit_text(
        get_text("admin_backup_restore_note", lang),
        reply_markup=get_back_to_settings_kb(lang)
    )


# ==================== НАВИГАЦИЯ ====================

@router.callback_query(F.data == "admin:settings:back")
async def back_to_settings_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Возврат в меню настроек.
    """
    await state.clear()
    await show_settings_menu(callback, session, state)


@router.callback_query(F.data.startswith("admin:settings:back:"))
async def back_to_specific_settings(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Возврат в конкретный раздел настроек.
    """
    target = callback.data.replace("admin:settings:back:", "")
    
    handlers = {
        "general": show_general_settings,
        "payment": show_payment_settings,
        "notifications": show_notification_settings,
        "admins": show_admins_list,
        "backup": show_backup_menu
    }
    
    handler = handlers.get(target)
    if handler:
        await handler(callback, session, state)
    else:
        await show_settings_menu(callback, session, state)


def setup_settings_handlers(dp):
    """Регистрация хэндлеров настроек."""
    dp.include_router(router)
