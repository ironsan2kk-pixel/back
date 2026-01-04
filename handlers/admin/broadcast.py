"""
Административный модуль: Рассылка сообщений
Чат 5.2 - Telegram бот продажи доступов к каналам

Функционал:
- Рассылка всем пользователям
- Рассылка по фильтрам (подписчики канала, пакета)
- Рассылка с медиа (фото, видео, документы)
- Предпросмотр перед отправкой
- Статистика рассылки
- Отложенная рассылка
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
import logging

from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, 
    Message,
    ContentType,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument
)
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    UserCRUD, SubscriptionCRUD, ChannelCRUD,
    PackageCRUD, BroadcastCRUD
)
from keyboards.admin_kb import (
    get_broadcast_menu_kb,
    get_broadcast_target_kb,
    get_broadcast_channels_kb,
    get_broadcast_packages_kb,
    get_broadcast_confirm_kb,
    get_broadcast_media_kb,
    get_broadcast_schedule_kb,
    get_back_to_broadcast_kb
)
from states.admin_states import BroadcastAdminState
from utils.i18n import get_text

router = Router()
logger = logging.getLogger(__name__)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def send_broadcast_message(
    bot: Bot,
    user_id: int,
    text: str,
    media_type: Optional[str] = None,
    media_file_id: Optional[str] = None,
    buttons: Optional[list] = None
) -> bool:
    """
    Отправка сообщения одному пользователю.
    
    Args:
        bot: Экземпляр бота
        user_id: Telegram ID пользователя
        text: Текст сообщения
        media_type: Тип медиа (photo, video, document)
        media_file_id: File ID медиа
        buttons: Кнопки (если есть)
        
    Returns:
        True если успешно, False если ошибка
    """
    try:
        if media_type == "photo" and media_file_id:
            await bot.send_photo(
                chat_id=user_id,
                photo=media_file_id,
                caption=text,
                parse_mode="HTML"
            )
        elif media_type == "video" and media_file_id:
            await bot.send_video(
                chat_id=user_id,
                video=media_file_id,
                caption=text,
                parse_mode="HTML"
            )
        elif media_type == "document" and media_file_id:
            await bot.send_document(
                chat_id=user_id,
                document=media_file_id,
                caption=text,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML"
            )
        return True
    except TelegramForbiddenError:
        # Пользователь заблокировал бота
        logger.warning(f"User {user_id} blocked the bot")
        return False
    except TelegramBadRequest as e:
        logger.error(f"Bad request for user {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending to user {user_id}: {e}")
        return False


async def get_target_users(
    session: AsyncSession,
    target_type: str,
    target_id: Optional[int] = None
) -> List[int]:
    """
    Получение списка пользователей для рассылки.
    
    Args:
        session: Сессия БД
        target_type: Тип таргета (all, active, channel, package)
        target_id: ID канала/пакета (если нужно)
        
    Returns:
        Список telegram_id пользователей
    """
    user_crud = UserCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    
    if target_type == "all":
        users = await user_crud.get_all_not_banned()
        return [u.telegram_id for u in users]
    
    elif target_type == "active":
        # Только пользователи с активными подписками
        users = await subscription_crud.get_users_with_active_subscriptions()
        return [u.telegram_id for u in users]
    
    elif target_type == "channel" and target_id:
        # Подписчики конкретного канала
        users = await subscription_crud.get_active_subscribers_by_channel(target_id)
        return [u.telegram_id for u in users]
    
    elif target_type == "package" and target_id:
        # Подписчики конкретного пакета
        users = await subscription_crud.get_active_subscribers_by_package(target_id)
        return [u.telegram_id for u in users]
    
    elif target_type == "inactive":
        # Пользователи без активных подписок
        users = await user_crud.get_users_without_active_subscriptions()
        return [u.telegram_id for u in users]
    
    elif target_type == "new":
        # Новые пользователи за последнюю неделю
        week_ago = datetime.utcnow() - timedelta(days=7)
        users = await user_crud.get_by_date_range(week_ago, datetime.utcnow())
        return [u.telegram_id for u in users if not u.is_banned]
    
    return []


# ==================== ГЛАВНОЕ МЕНЮ РАССЫЛКИ ====================

@router.callback_query(F.data == "admin:broadcast")
async def show_broadcast_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Главное меню рассылки.
    """
    await state.clear()
    lang = callback.from_user.language_code or "ru"
    
    # Статистика предыдущих рассылок
    broadcast_crud = BroadcastCRUD(session)
    
    last_broadcast = await broadcast_crud.get_last()
    total_broadcasts = await broadcast_crud.count_all()
    
    if last_broadcast:
        last_info = get_text("admin_broadcast_last_info", lang).format(
            date=last_broadcast.created_at.strftime("%d.%m.%Y %H:%M"),
            sent=last_broadcast.sent_count,
            failed=last_broadcast.failed_count
        )
    else:
        last_info = get_text("admin_broadcast_no_history", lang)
    
    text = get_text("admin_broadcast_menu", lang).format(
        total_broadcasts=total_broadcasts,
        last_info=last_info
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_broadcast_menu_kb(lang)
    )
    await callback.answer()


# ==================== СОЗДАНИЕ РАССЫЛКИ ====================

@router.callback_query(F.data == "admin:broadcast:new")
async def start_new_broadcast(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Начало создания новой рассылки.
    Выбор целевой аудитории.
    """
    lang = callback.from_user.language_code or "ru"
    
    user_crud = UserCRUD(session)
    subscription_crud = SubscriptionCRUD(session)
    
    # Подсчёт аудиторий
    all_users = await user_crud.count_not_banned()
    active_users = await subscription_crud.count_users_with_active_subscriptions()
    inactive_users = all_users - active_users
    
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = await user_crud.count_by_date_range(week_ago, datetime.utcnow())
    
    await state.set_state(BroadcastAdminState.selecting_target)
    
    text = get_text("admin_broadcast_select_target", lang).format(
        all_users=all_users,
        active_users=active_users,
        inactive_users=inactive_users,
        new_users=new_users
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_broadcast_target_kb(lang)
    )
    await callback.answer()


@router.callback_query(
    BroadcastAdminState.selecting_target,
    F.data.startswith("admin:broadcast:target:")
)
async def select_broadcast_target(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Обработка выбора целевой аудитории.
    """
    lang = callback.from_user.language_code or "ru"
    target = callback.data.split(":")[-1]
    
    if target == "channel":
        # Показываем список каналов
        channel_crud = ChannelCRUD(session)
        channels = await channel_crud.get_all_active()
        
        if not channels:
            await callback.answer(
                get_text("admin_broadcast_no_channels", lang),
                show_alert=True
            )
            return
        
        await state.set_state(BroadcastAdminState.selecting_channel)
        
        text = get_text("admin_broadcast_select_channel", lang)
        await callback.message.edit_text(
            text,
            reply_markup=get_broadcast_channels_kb(channels, lang)
        )
        
    elif target == "package":
        # Показываем список пакетов
        package_crud = PackageCRUD(session)
        packages = await package_crud.get_all_active()
        
        if not packages:
            await callback.answer(
                get_text("admin_broadcast_no_packages", lang),
                show_alert=True
            )
            return
        
        await state.set_state(BroadcastAdminState.selecting_package)
        
        text = get_text("admin_broadcast_select_package", lang)
        await callback.message.edit_text(
            text,
            reply_markup=get_broadcast_packages_kb(packages, lang)
        )
        
    else:
        # all, active, inactive, new - сразу переходим к вводу текста
        await state.update_data(
            target_type=target,
            target_id=None
        )
        await state.set_state(BroadcastAdminState.entering_text)
        
        text = get_text("admin_broadcast_enter_text", lang)
        await callback.message.edit_text(
            text,
            reply_markup=get_back_to_broadcast_kb(lang)
        )
    
    await callback.answer()


@router.callback_query(
    BroadcastAdminState.selecting_channel,
    F.data.startswith("admin:broadcast:channel:")
)
async def select_broadcast_channel(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Выбор канала для рассылки.
    """
    lang = callback.from_user.language_code or "ru"
    channel_id = int(callback.data.split(":")[-1])
    
    await state.update_data(
        target_type="channel",
        target_id=channel_id
    )
    await state.set_state(BroadcastAdminState.entering_text)
    
    text = get_text("admin_broadcast_enter_text", lang)
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_broadcast_kb(lang)
    )
    await callback.answer()


@router.callback_query(
    BroadcastAdminState.selecting_package,
    F.data.startswith("admin:broadcast:package:")
)
async def select_broadcast_package(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Выбор пакета для рассылки.
    """
    lang = callback.from_user.language_code or "ru"
    package_id = int(callback.data.split(":")[-1])
    
    await state.update_data(
        target_type="package",
        target_id=package_id
    )
    await state.set_state(BroadcastAdminState.entering_text)
    
    text = get_text("admin_broadcast_enter_text", lang)
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_broadcast_kb(lang)
    )
    await callback.answer()


# ==================== ВВОД ТЕКСТА ====================

@router.message(BroadcastAdminState.entering_text)
async def process_broadcast_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Обработка текста рассылки.
    """
    lang = message.from_user.language_code or "ru"
    
    if not message.text and not message.caption:
        await message.answer(get_text("admin_broadcast_text_required", lang))
        return
    
    text = message.text or message.caption
    
    if len(text) > 4000:
        await message.answer(
            get_text("admin_broadcast_text_too_long", lang).format(max_length=4000)
        )
        return
    
    await state.update_data(broadcast_text=text)
    await state.set_state(BroadcastAdminState.adding_media)
    
    await message.answer(
        get_text("admin_broadcast_add_media", lang),
        reply_markup=get_broadcast_media_kb(lang)
    )


# ==================== ДОБАВЛЕНИЕ МЕДИА ====================

@router.callback_query(
    BroadcastAdminState.adding_media,
    F.data == "admin:broadcast:skip_media"
)
async def skip_broadcast_media(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Пропуск добавления медиа.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.update_data(
        media_type=None,
        media_file_id=None
    )
    
    await show_broadcast_preview(callback, session, state)


@router.message(
    BroadcastAdminState.adding_media,
    F.photo
)
async def process_broadcast_photo(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Обработка фото для рассылки.
    """
    file_id = message.photo[-1].file_id
    
    await state.update_data(
        media_type="photo",
        media_file_id=file_id
    )
    
    # Показываем предпросмотр
    await show_broadcast_preview_message(message, session, state)


@router.message(
    BroadcastAdminState.adding_media,
    F.video
)
async def process_broadcast_video(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Обработка видео для рассылки.
    """
    file_id = message.video.file_id
    
    await state.update_data(
        media_type="video",
        media_file_id=file_id
    )
    
    await show_broadcast_preview_message(message, session, state)


@router.message(
    BroadcastAdminState.adding_media,
    F.document
)
async def process_broadcast_document(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Обработка документа для рассылки.
    """
    file_id = message.document.file_id
    
    await state.update_data(
        media_type="document",
        media_file_id=file_id
    )
    
    await show_broadcast_preview_message(message, session, state)


# ==================== ПРЕДПРОСМОТР ====================

async def show_broadcast_preview(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Показ предпросмотра рассылки (из callback).
    """
    lang = callback.from_user.language_code or "ru"
    data = await state.get_data()
    
    target_type = data.get("target_type", "all")
    target_id = data.get("target_id")
    broadcast_text = data.get("broadcast_text", "")
    media_type = data.get("media_type")
    media_file_id = data.get("media_file_id")
    
    # Получаем количество получателей
    recipients = await get_target_users(session, target_type, target_id)
    recipients_count = len(recipients)
    
    # Название таргета
    target_names = {
        "all": get_text("broadcast_target_all", lang),
        "active": get_text("broadcast_target_active", lang),
        "inactive": get_text("broadcast_target_inactive", lang),
        "new": get_text("broadcast_target_new", lang),
        "channel": get_text("broadcast_target_channel", lang),
        "package": get_text("broadcast_target_package", lang)
    }
    
    target_name = target_names.get(target_type, target_type)
    
    if target_type == "channel" and target_id:
        channel_crud = ChannelCRUD(session)
        channel = await channel_crud.get_by_id(target_id)
        if channel:
            target_name = f"{target_name}: {channel.name}"
    elif target_type == "package" and target_id:
        package_crud = PackageCRUD(session)
        package = await package_crud.get_by_id(target_id)
        if package:
            target_name = f"{target_name}: {package.name}"
    
    media_info = get_text("broadcast_no_media", lang)
    if media_type:
        media_names = {
            "photo": get_text("broadcast_media_photo", lang),
            "video": get_text("broadcast_media_video", lang),
            "document": get_text("broadcast_media_document", lang)
        }
        media_info = media_names.get(media_type, media_type)
    
    await state.set_state(BroadcastAdminState.confirming)
    
    preview_text = get_text("admin_broadcast_preview", lang).format(
        target=target_name,
        recipients=recipients_count,
        media=media_info,
        text=broadcast_text[:500] + "..." if len(broadcast_text) > 500 else broadcast_text
    )
    
    await callback.message.edit_text(
        preview_text,
        reply_markup=get_broadcast_confirm_kb(lang)
    )
    await callback.answer()


async def show_broadcast_preview_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Показ предпросмотра рассылки (из message).
    """
    lang = message.from_user.language_code or "ru"
    data = await state.get_data()
    
    target_type = data.get("target_type", "all")
    target_id = data.get("target_id")
    broadcast_text = data.get("broadcast_text", "")
    media_type = data.get("media_type")
    
    # Получаем количество получателей
    recipients = await get_target_users(session, target_type, target_id)
    recipients_count = len(recipients)
    
    # Название таргета
    target_names = {
        "all": get_text("broadcast_target_all", lang),
        "active": get_text("broadcast_target_active", lang),
        "inactive": get_text("broadcast_target_inactive", lang),
        "new": get_text("broadcast_target_new", lang),
        "channel": get_text("broadcast_target_channel", lang),
        "package": get_text("broadcast_target_package", lang)
    }
    
    target_name = target_names.get(target_type, target_type)
    
    if target_type == "channel" and target_id:
        channel_crud = ChannelCRUD(session)
        channel = await channel_crud.get_by_id(target_id)
        if channel:
            target_name = f"{target_name}: {channel.name}"
    elif target_type == "package" and target_id:
        package_crud = PackageCRUD(session)
        package = await package_crud.get_by_id(target_id)
        if package:
            target_name = f"{target_name}: {package.name}"
    
    media_info = get_text("broadcast_no_media", lang)
    if media_type:
        media_names = {
            "photo": get_text("broadcast_media_photo", lang),
            "video": get_text("broadcast_media_video", lang),
            "document": get_text("broadcast_media_document", lang)
        }
        media_info = media_names.get(media_type, media_type)
    
    await state.set_state(BroadcastAdminState.confirming)
    
    preview_text = get_text("admin_broadcast_preview", lang).format(
        target=target_name,
        recipients=recipients_count,
        media=media_info,
        text=broadcast_text[:500] + "..." if len(broadcast_text) > 500 else broadcast_text
    )
    
    await message.answer(
        preview_text,
        reply_markup=get_broadcast_confirm_kb(lang)
    )


# ==================== ПОДТВЕРЖДЕНИЕ И ОТПРАВКА ====================

@router.callback_query(
    BroadcastAdminState.confirming,
    F.data == "admin:broadcast:send_now"
)
async def send_broadcast_now(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot
):
    """
    Немедленная отправка рассылки.
    """
    lang = callback.from_user.language_code or "ru"
    data = await state.get_data()
    
    target_type = data.get("target_type", "all")
    target_id = data.get("target_id")
    broadcast_text = data.get("broadcast_text", "")
    media_type = data.get("media_type")
    media_file_id = data.get("media_file_id")
    
    # Получаем получателей
    recipients = await get_target_users(session, target_type, target_id)
    total = len(recipients)
    
    if total == 0:
        await callback.answer(
            get_text("admin_broadcast_no_recipients", lang),
            show_alert=True
        )
        return
    
    await callback.answer()
    
    # Статус сообщение
    status_message = await callback.message.edit_text(
        get_text("admin_broadcast_sending", lang).format(
            sent=0,
            total=total,
            progress="0%"
        )
    )
    
    # Отправка
    sent_count = 0
    failed_count = 0
    blocked_users = []
    
    for i, user_id in enumerate(recipients):
        success = await send_broadcast_message(
            bot=bot,
            user_id=user_id,
            text=broadcast_text,
            media_type=media_type,
            media_file_id=media_file_id
        )
        
        if success:
            sent_count += 1
        else:
            failed_count += 1
            blocked_users.append(user_id)
        
        # Обновляем статус каждые 50 сообщений
        if (i + 1) % 50 == 0 or i == total - 1:
            progress = (i + 1) / total * 100
            try:
                await status_message.edit_text(
                    get_text("admin_broadcast_sending", lang).format(
                        sent=sent_count,
                        total=total,
                        progress=f"{progress:.1f}%"
                    )
                )
            except:
                pass
        
        # Задержка для избежания флуда
        await asyncio.sleep(0.05)
    
    # Сохраняем рассылку в БД
    broadcast_crud = BroadcastCRUD(session)
    await broadcast_crud.create(
        admin_id=callback.from_user.id,
        target_type=target_type,
        target_id=target_id,
        text=broadcast_text,
        media_type=media_type,
        media_file_id=media_file_id,
        sent_count=sent_count,
        failed_count=failed_count
    )
    
    # Обновляем заблокированных пользователей
    if blocked_users:
        user_crud = UserCRUD(session)
        for user_id in blocked_users:
            await user_crud.mark_as_blocked(user_id)
    
    await state.clear()
    
    # Итоговое сообщение
    await status_message.edit_text(
        get_text("admin_broadcast_completed", lang).format(
            sent=sent_count,
            failed=failed_count,
            total=total
        ),
        reply_markup=get_broadcast_menu_kb(lang)
    )


@router.callback_query(
    BroadcastAdminState.confirming,
    F.data == "admin:broadcast:schedule"
)
async def schedule_broadcast(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Отложенная рассылка - выбор времени.
    """
    lang = callback.from_user.language_code or "ru"
    
    await state.set_state(BroadcastAdminState.scheduling)
    
    text = get_text("admin_broadcast_schedule_time", lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_broadcast_schedule_kb(lang)
    )
    await callback.answer()


@router.callback_query(
    BroadcastAdminState.scheduling,
    F.data.startswith("admin:broadcast:schedule:")
)
async def process_schedule_time(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Обработка выбора времени отложенной рассылки.
    """
    lang = callback.from_user.language_code or "ru"
    delay = callback.data.split(":")[-1]
    
    now = datetime.utcnow()
    
    delay_map = {
        "1h": timedelta(hours=1),
        "3h": timedelta(hours=3),
        "6h": timedelta(hours=6),
        "12h": timedelta(hours=12),
        "24h": timedelta(hours=24)
    }
    
    if delay not in delay_map:
        await callback.answer(
            get_text("admin_broadcast_invalid_delay", lang),
            show_alert=True
        )
        return
    
    scheduled_time = now + delay_map[delay]
    
    data = await state.get_data()
    
    # Сохраняем отложенную рассылку
    broadcast_crud = BroadcastCRUD(session)
    await broadcast_crud.create_scheduled(
        admin_id=callback.from_user.id,
        target_type=data.get("target_type", "all"),
        target_id=data.get("target_id"),
        text=data.get("broadcast_text", ""),
        media_type=data.get("media_type"),
        media_file_id=data.get("media_file_id"),
        scheduled_at=scheduled_time
    )
    
    await state.clear()
    
    await callback.message.edit_text(
        get_text("admin_broadcast_scheduled", lang).format(
            time=scheduled_time.strftime("%d.%m.%Y %H:%M UTC")
        ),
        reply_markup=get_broadcast_menu_kb(lang)
    )
    await callback.answer()


@router.message(BroadcastAdminState.scheduling)
async def process_custom_schedule_time(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Обработка кастомного времени отложенной рассылки.
    Формат: DD.MM.YYYY HH:MM
    """
    lang = message.from_user.language_code or "ru"
    
    try:
        scheduled_time = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(
            get_text("admin_broadcast_invalid_time_format", lang)
        )
        return
    
    if scheduled_time <= datetime.utcnow():
        await message.answer(
            get_text("admin_broadcast_time_in_past", lang)
        )
        return
    
    data = await state.get_data()
    
    # Сохраняем отложенную рассылку
    broadcast_crud = BroadcastCRUD(session)
    await broadcast_crud.create_scheduled(
        admin_id=message.from_user.id,
        target_type=data.get("target_type", "all"),
        target_id=data.get("target_id"),
        text=data.get("broadcast_text", ""),
        media_type=data.get("media_type"),
        media_file_id=data.get("media_file_id"),
        scheduled_at=scheduled_time
    )
    
    await state.clear()
    
    await message.answer(
        get_text("admin_broadcast_scheduled", lang).format(
            time=scheduled_time.strftime("%d.%m.%Y %H:%M UTC")
        ),
        reply_markup=get_broadcast_menu_kb(lang)
    )


# ==================== ИСТОРИЯ РАССЫЛОК ====================

@router.callback_query(F.data == "admin:broadcast:history")
async def show_broadcast_history(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    История рассылок.
    """
    lang = callback.from_user.language_code or "ru"
    
    broadcast_crud = BroadcastCRUD(session)
    broadcasts = await broadcast_crud.get_recent(limit=10)
    
    if not broadcasts:
        text = get_text("admin_broadcast_history_empty", lang)
    else:
        items = []
        for bc in broadcasts:
            status = "✅" if bc.sent_count > 0 else "⏳" if bc.scheduled_at else "❌"
            
            target_names = {
                "all": "Все",
                "active": "Активные",
                "inactive": "Неактивные",
                "new": "Новые",
                "channel": "Канал",
                "package": "Пакет"
            }
            target = target_names.get(bc.target_type, bc.target_type)
            
            items.append(
                f"{status} {bc.created_at.strftime('%d.%m %H:%M')} | "
                f"{target} | ✉️ {bc.sent_count}/{bc.sent_count + bc.failed_count}"
            )
        
        text = get_text("admin_broadcast_history", lang).format(
            history="\n".join(items)
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_broadcast_kb(lang)
    )
    await callback.answer()


# ==================== ОТЛОЖЕННЫЕ РАССЫЛКИ ====================

@router.callback_query(F.data == "admin:broadcast:scheduled")
async def show_scheduled_broadcasts(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Список отложенных рассылок.
    """
    lang = callback.from_user.language_code or "ru"
    
    broadcast_crud = BroadcastCRUD(session)
    scheduled = await broadcast_crud.get_scheduled()
    
    if not scheduled:
        text = get_text("admin_broadcast_no_scheduled", lang)
    else:
        items = []
        for i, bc in enumerate(scheduled, 1):
            target_names = {
                "all": "Все",
                "active": "Активные",
                "inactive": "Неактивные",
                "new": "Новые",
                "channel": "Канал",
                "package": "Пакет"
            }
            target = target_names.get(bc.target_type, bc.target_type)
            
            items.append(
                f"{i}. ⏰ {bc.scheduled_at.strftime('%d.%m.%Y %H:%M')} | {target}\n"
                f"   📝 {bc.text[:50]}..."
            )
        
        text = get_text("admin_broadcast_scheduled_list", lang).format(
            broadcasts="\n\n".join(items)
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_broadcast_kb(lang)
    )
    await callback.answer()


# ==================== ОТМЕНА ====================

@router.callback_query(
    BroadcastAdminState.confirming,
    F.data == "admin:broadcast:cancel"
)
async def cancel_broadcast(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Отмена рассылки.
    """
    await state.clear()
    await show_broadcast_menu(callback, session, state)


@router.callback_query(F.data == "admin:broadcast:back")
async def back_to_broadcast_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Возврат в меню рассылки.
    """
    await state.clear()
    await show_broadcast_menu(callback, session, state)


def setup_broadcast_handlers(dp):
    """Регистрация хэндлеров рассылки."""
    dp.include_router(router)
