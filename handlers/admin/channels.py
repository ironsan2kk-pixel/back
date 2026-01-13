"""
═══════════════════════════════════════════════════════════════════════════════
📢 УПРАВЛЕНИЕ КАНАЛАМИ
═══════════════════════════════════════════════════════════════════════════════
Полное управление каналами: список, добавление, редактирование, удаление.

Функционал:
- Просмотр списка каналов с пагинацией
- Добавление нового канала (пошаговый визард)
- Редактирование всех полей канала
- Управление пробным периодом
- Активация/деактивация
- Изменение порядка отображения
- Удаление канала
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from database.crud import ChannelCRUD, SubscriptionCRUD
from keyboards.admin_kb import (
    get_channels_menu,
    get_channels_list_keyboard,
    get_channel_detail_keyboard,
    get_channel_trial_keyboard,
    get_channel_order_keyboard,
    get_channel_position_keyboard,
    get_confirm_cancel_keyboard,
    get_back_button,
    get_skip_button,
)
from states.admin_states import ChannelAddState, ChannelEditState, ChannelOrderState, TrialSettingsState
from handlers.admin.main import check_admin

logger = logging.getLogger(__name__)

router = Router(name="admin_channels")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 СПИСОК КАНАЛОВ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:channels:list")
async def callback_channels_list(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Показать список всех каналов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await show_channels_list(callback.message, session, page=0, edit=True)


@router.callback_query(F.data.startswith("admin:channels:list:"))
async def callback_channels_list_page(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Пагинация списка каналов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    page = int(callback.data.split(":")[-1])
    await callback.answer()
    await show_channels_list(callback.message, session, page=page, edit=True)


async def show_channels_list(
    message: Message,
    session: AsyncSession,
    page: int = 0,
    edit: bool = False
):
    """Отображение списка каналов."""
    channels = await ChannelCRUD.get_all(session, order_by="sort_order")
    
    # Преобразуем в список словарей для клавиатуры
    channels_data = []
    for channel in channels:
        # Получаем количество активных подписок
        subs_count = await SubscriptionCRUD.count_by_channel(session, channel.id)
        channels_data.append({
            "id": channel.id,
            "name_ru": channel.name_ru,
            "is_active": channel.is_active,
            "subscribers_count": subs_count,
        })
    
    if not channels_data:
        text = """
📢 <b>Каналы</b>

━━━━━━━━━━━━━━━━━━━━━━
📭 Каналов пока нет.

Нажмите «Добавить», чтобы создать первый канал.
"""
    else:
        text = f"""
📢 <b>Список каналов</b>

━━━━━━━━━━━━━━━━━━━━━━
Всего: <b>{len(channels_data)}</b> каналов

✅ = активен | ❌ = неактивен
Число в скобках — активные подписки
━━━━━━━━━━━━━━━━━━━━━━

Выберите канал для управления:
"""
    
    keyboard = get_channels_list_keyboard(channels_data, page=page)
    
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
# 👁️ ПРОСМОТР КАНАЛА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:channels:view:"))
async def callback_channel_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Просмотр детальной информации о канале."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    channel_id = int(callback.data.split(":")[-1])
    await callback.answer()
    await show_channel_detail(callback.message, session, channel_id)


async def show_channel_detail(
    message: Message,
    session: AsyncSession,
    channel_id: int
):
    """Отображение детальной информации о канале."""
    channel = await ChannelCRUD.get_by_id(session, channel_id)
    
    if not channel:
        await message.edit_text(
            "❌ Канал не найден.",
            reply_markup=get_back_button("admin:channels:list")
        )
        return
    
    # Получаем статистику
    subs_count = await SubscriptionCRUD.count_by_channel(session, channel_id)
    active_subs = await SubscriptionCRUD.count_active_by_channel(session, channel_id)
    
    # Статус
    status = "✅ Активен" if channel.is_active else "❌ Неактивен"
    
    # Пробный период
    if channel.trial_enabled:
        trial_text = f"✅ Включён ({channel.trial_days} дн.)"
    else:
        trial_text = "❌ Выключен"
    
    text = f"""
📢 <b>Канал: {channel.name_ru}</b>

━━━━━━━━━━━━━━━━━━━━━━
📌 <b>Основная информация</b>
━━━━━━━━━━━━━━━━━━━━━━

🆔 ID в боте: <code>{channel.id}</code>
📱 Telegram ID: <code>{channel.telegram_id}</code>
🔗 Username: @{channel.username or '—'}

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Названия</b>
━━━━━━━━━━━━━━━━━━━━━━

🇷🇺 RU: {channel.name_ru}
🇬🇧 EN: {channel.name_en or '—'}

━━━━━━━━━━━━━━━━━━━━━━
📄 <b>Описания</b>
━━━━━━━━━━━━━━━━━━━━━━

🇷🇺 RU: {channel.description_ru or '—'}
🇬🇧 EN: {channel.description_en or '—'}

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Статистика</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 Всего подписок: <b>{subs_count}</b>
✅ Активных: <b>{active_subs}</b>
📍 Статус: <b>{status}</b>
🎁 Пробный период: <b>{trial_text}</b>
📷 Изображение: {'✅ Есть' if channel.image_file_id else '❌ Нет'}

━━━━━━━━━━━━━━━━━━━━━━
Выберите действие:
"""
    
    await message.edit_text(
        text,
        reply_markup=get_channel_detail_keyboard(channel_id, channel.is_active),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ ДОБАВЛЕНИЕ КАНАЛА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:channels:add")
async def callback_channel_add_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Начало добавления канала."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(ChannelAddState.waiting_channel_id)
    
    text = """
➕ <b>Добавление канала</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>Шаг 1/6:</b> ID или username канала
━━━━━━━━━━━━━━━━━━━━━━

Отправьте ID канала (число с минусом) или
@username канала.

<b>Примеры:</b>
• <code>-1001234567890</code>
• <code>@my_channel</code>

⚠️ Бот должен быть администратором канала
с правом приглашения пользователей!
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_button("admin:channels", "❌ Отмена"),
        parse_mode="HTML"
    )


@router.message(ChannelAddState.waiting_channel_id)
async def process_channel_id(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot
):
    """Обработка введённого ID канала."""
    if not await check_admin(message, session):
        return
    
    channel_input = message.text.strip()
    
    try:
        # Пробуем получить информацию о канале
        if channel_input.startswith("@"):
            chat = await bot.get_chat(channel_input)
        else:
            chat = await bot.get_chat(int(channel_input))
        
        # Проверяем, что это канал
        if chat.type != "channel":
            await message.answer(
                "❌ Это не канал. Пожалуйста, отправьте ID канала.",
                reply_markup=get_back_button("admin:channels:add", "🔄 Попробовать снова")
            )
            return
        
        # Проверяем права бота
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if not bot_member.can_invite_users:
            await message.answer(
                "⚠️ Бот не имеет права приглашать пользователей в этот канал.\n\n"
                "Добавьте бота как администратора с правом «Приглашение пользователей».",
                reply_markup=get_back_button("admin:channels:add", "🔄 Попробовать снова")
            )
            return
        
        # Проверяем, не добавлен ли уже
        existing = await ChannelCRUD.get_by_telegram_id(session, chat.id)
        if existing:
            await message.answer(
                f"⚠️ Канал «{existing.name_ru}» уже добавлен в систему.",
                reply_markup=get_back_button("admin:channels:list")
            )
            await state.clear()
            return
        
        # Сохраняем данные
        await state.update_data(
            telegram_id=chat.id,
            username=chat.username,
            chat_title=chat.title
        )
        await state.set_state(ChannelAddState.waiting_name_ru)
        
        text = f"""
➕ <b>Добавление канала</b>

━━━━━━━━━━━━━━━━━━━━━━
✅ Канал найден: <b>{chat.title}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 2/6:</b> Название на русском

Введите название канала для отображения
в боте на русском языке.

<i>Можно использовать оригинальное название
или своё кастомное.</i>
"""
        await message.answer(
            text,
            reply_markup=get_back_button("admin:channels:add", "❌ Отмена"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Failed to get channel info: {e}")
        await message.answer(
            "❌ Не удалось найти канал.\n\n"
            "Проверьте:\n"
            "• Правильность ID/username\n"
            "• Бот добавлен в канал как администратор",
            reply_markup=get_back_button("admin:channels:add", "🔄 Попробовать снова")
        )


@router.message(ChannelAddState.waiting_name_ru)
async def process_name_ru(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка названия на русском."""
    if not await check_admin(message, session):
        return
    
    name_ru = message.text.strip()
    
    if len(name_ru) > 100:
        await message.answer("❌ Название слишком длинное (макс. 100 символов)")
        return
    
    await state.update_data(name_ru=name_ru)
    await state.set_state(ChannelAddState.waiting_name_en)
    
    text = f"""
➕ <b>Добавление канала</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 Название RU: <b>{name_ru}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 3/6:</b> Название на английском

Введите название канала на английском языке.
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [get_skip_button("admin:channels:add:skip:name_en")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:channels")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:channels:add:skip:name_en")
async def skip_name_en(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Пропуск английского названия."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    data = await state.get_data()
    await state.update_data(name_en=data.get("name_ru"))  # Копируем русское
    await state.set_state(ChannelAddState.waiting_description_ru)
    
    await ask_description_ru(callback.message, data.get("name_ru"), data.get("name_ru"))


@router.message(ChannelAddState.waiting_name_en)
async def process_name_en(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка названия на английском."""
    if not await check_admin(message, session):
        return
    
    name_en = message.text.strip()
    
    if len(name_en) > 100:
        await message.answer("❌ Название слишком длинное (макс. 100 символов)")
        return
    
    data = await state.get_data()
    await state.update_data(name_en=name_en)
    await state.set_state(ChannelAddState.waiting_description_ru)
    
    await ask_description_ru(message, data.get("name_ru"), name_en)


async def ask_description_ru(message: Message, name_ru: str, name_en: str):
    """Запрос описания на русском."""
    text = f"""
➕ <b>Добавление канала</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 Название RU: <b>{name_ru}</b>
🇬🇧 Название EN: <b>{name_en}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 4/6:</b> Описание на русском

Введите описание канала на русском языке.
Это будет отображаться при выборе канала.
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [get_skip_button("admin:channels:add:skip:desc_ru")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:channels")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:channels:add:skip:desc_ru")
async def skip_desc_ru(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Пропуск русского описания."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await state.update_data(description_ru=None)
    await state.set_state(ChannelAddState.waiting_description_en)
    
    data = await state.get_data()
    await ask_description_en(callback.message, data)


@router.message(ChannelAddState.waiting_description_ru)
async def process_description_ru(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка описания на русском."""
    if not await check_admin(message, session):
        return
    
    description_ru = message.text.strip()
    
    if len(description_ru) > 500:
        await message.answer("❌ Описание слишком длинное (макс. 500 символов)")
        return
    
    await state.update_data(description_ru=description_ru)
    await state.set_state(ChannelAddState.waiting_description_en)
    
    data = await state.get_data()
    await ask_description_en(message, data)


async def ask_description_en(message: Message, data: dict):
    """Запрос описания на английском."""
    text = f"""
➕ <b>Добавление канала</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 Название: <b>{data.get('name_ru')}</b>
🇬🇧 Название: <b>{data.get('name_en')}</b>
📝 Описание RU: {data.get('description_ru') or '—'}
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 5/6:</b> Описание на английском

Введите описание канала на английском языке.
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [get_skip_button("admin:channels:add:skip:desc_en")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:channels")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:channels:add:skip:desc_en")
async def skip_desc_en(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Пропуск английского описания."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await state.update_data(description_en=None)
    await state.set_state(ChannelAddState.waiting_image)
    
    data = await state.get_data()
    await ask_image(callback.message, data)


@router.message(ChannelAddState.waiting_description_en)
async def process_description_en(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка описания на английском."""
    if not await check_admin(message, session):
        return
    
    description_en = message.text.strip()
    
    if len(description_en) > 500:
        await message.answer("❌ Описание слишком длинное (макс. 500 символов)")
        return
    
    await state.update_data(description_en=description_en)
    await state.set_state(ChannelAddState.waiting_image)
    
    data = await state.get_data()
    await ask_image(message, data)


async def ask_image(message: Message, data: dict):
    """Запрос изображения канала."""
    text = f"""
➕ <b>Добавление канала</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 {data.get('name_ru')}
🇬🇧 {data.get('name_en')}
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 6/6:</b> Изображение канала

Отправьте изображение для отображения
в каталоге (рекомендуемый размер 400x400).

Или пропустите этот шаг.
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [get_skip_button("admin:channels:add:skip:image")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:channels")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:channels:add:skip:image")
async def skip_image(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Пропуск изображения."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await state.update_data(image_file_id=None)
    await state.set_state(ChannelAddState.confirm)
    
    data = await state.get_data()
    await show_channel_confirm(callback.message, data)


@router.message(ChannelAddState.waiting_image, F.photo)
async def process_image(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка изображения."""
    if not await check_admin(message, session):
        return
    
    # Берём самое большое фото
    photo = message.photo[-1]
    
    await state.update_data(image_file_id=photo.file_id)
    await state.set_state(ChannelAddState.confirm)
    
    data = await state.get_data()
    await show_channel_confirm(message, data)


@router.message(ChannelAddState.waiting_image)
async def process_image_invalid(message: Message, session: AsyncSession):
    """Обработка неверного формата изображения."""
    if not await check_admin(message, session):
        return
    
    await message.answer("❌ Пожалуйста, отправьте изображение или нажмите «Пропустить»")


async def show_channel_confirm(message: Message, data: dict):
    """Показ подтверждения создания канала."""
    text = f"""
➕ <b>Подтверждение создания канала</b>

━━━━━━━━━━━━━━━━━━━━━━
📱 Telegram: <code>{data.get('telegram_id')}</code>
{'🔗 Username: @' + data.get('username') if data.get('username') else ''}

🇷🇺 <b>Русский:</b>
   • Название: {data.get('name_ru')}
   • Описание: {data.get('description_ru') or '—'}

🇬🇧 <b>English:</b>
   • Name: {data.get('name_en')}
   • Description: {data.get('description_en') or '—'}

🖼️ Изображение: {'✅ Загружено' if data.get('image_file_id') else '❌ Нет'}
━━━━━━━━━━━━━━━━━━━━━━

Создать канал?
"""
    
    await message.answer(
        text,
        reply_markup=get_confirm_cancel_keyboard(
            "admin:channels:add:confirm",
            "admin:channels"
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:channels:add:confirm")
async def confirm_channel_add(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Подтверждение создания канала."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    await state.clear()
    
    try:
        # Получаем следующий sort_order
        channels = await ChannelCRUD.get_all(session)
        max_sort = max((c.sort_order for c in channels), default=0)
        
        # Создаём канал
        channel = await ChannelCRUD.create(
            session,
            telegram_id=data["telegram_id"],
            username=data.get("username"),
            name_ru=data["name_ru"],
            name_en=data.get("name_en"),
            description_ru=data.get("description_ru"),
            description_en=data.get("description_en"),
            image_file_id=data.get("image_file_id"),
            sort_order=max_sort + 1,
            is_active=True
        )
        
        await callback.answer("✅ Канал создан!")
        
        # Показываем созданный канал
        await show_channel_detail(callback.message, session, channel.id)
        
        logger.info(
            f"Channel created: id={channel.id}, name={channel.name_ru}, "
            f"admin_id={callback.from_user.id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to create channel: {e}")
        await callback.answer("❌ Ошибка создания канала", show_alert=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании канала.\n\n"
            f"Ошибка: {str(e)}",
            reply_markup=get_back_button("admin:channels")
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ✏️ РЕДАКТИРОВАНИЕ КАНАЛА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:channels:edit:"))
async def callback_channel_edit(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Начало редактирования поля канала."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    channel_id = int(parts[3])
    field = parts[4]
    
    channel = await ChannelCRUD.get_by_id(session, channel_id)
    if not channel:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(ChannelEditState.waiting_new_value)
    await state.update_data(channel_id=channel_id, field=field)
    
    field_labels = {
        "name_ru": ("🇷🇺 Название (RU)", channel.name_ru),
        "name_en": ("🇬🇧 Название (EN)", channel.name_en),
        "desc_ru": ("🇷🇺 Описание (RU)", channel.description_ru),
        "desc_en": ("🇬🇧 Описание (EN)", channel.description_en),
        "image": ("🖼️ Изображение", "Загружено" if channel.image_file_id else "Нет"),
    }
    
    label, current = field_labels.get(field, ("Поле", "—"))
    
    if field == "image":
        text = f"""
✏️ <b>Редактирование: {label}</b>

━━━━━━━━━━━━━━━━━━━━━━
Текущее значение: <b>{current}</b>
━━━━━━━━━━━━━━━━━━━━━━

Отправьте новое изображение:
"""
        await state.set_state(ChannelEditState.waiting_image)
    else:
        text = f"""
✏️ <b>Редактирование: {label}</b>

━━━━━━━━━━━━━━━━━━━━━━
Текущее значение: <b>{current or '—'}</b>
━━━━━━━━━━━━━━━━━━━━━━

Введите новое значение:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_button(f"admin:channels:view:{channel_id}", "❌ Отмена"),
        parse_mode="HTML"
    )


@router.message(ChannelEditState.waiting_new_value)
async def process_edit_value(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка нового значения поля."""
    if not await check_admin(message, session):
        return
    
    data = await state.get_data()
    channel_id = data["channel_id"]
    field = data["field"]
    new_value = message.text.strip()
    
    # Маппинг полей
    field_map = {
        "name_ru": "name_ru",
        "name_en": "name_en",
        "desc_ru": "description_ru",
        "desc_en": "description_en",
    }
    
    db_field = field_map.get(field)
    if not db_field:
        await message.answer("❌ Неизвестное поле")
        await state.clear()
        return
    
    # Валидация
    if db_field.startswith("name") and len(new_value) > 100:
        await message.answer("❌ Название слишком длинное (макс. 100 символов)")
        return
    
    if db_field.startswith("description") and len(new_value) > 500:
        await message.answer("❌ Описание слишком длинное (макс. 500 символов)")
        return
    
    try:
        await ChannelCRUD.update(session, channel_id, **{db_field: new_value})
        await state.clear()
        await message.answer("✅ Сохранено!")
        
        # Возвращаемся к просмотру канала
        await show_channel_detail(message, session, channel_id)
        
    except Exception as e:
        logger.error(f"Failed to update channel: {e}")
        await message.answer("❌ Ошибка сохранения")


@router.message(ChannelEditState.waiting_image, F.photo)
async def process_edit_image(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка нового изображения."""
    if not await check_admin(message, session):
        return
    
    data = await state.get_data()
    channel_id = data["channel_id"]
    photo = message.photo[-1]
    
    try:
        await ChannelCRUD.update(session, channel_id, image_file_id=photo.file_id)
        await state.clear()
        await message.answer("✅ Изображение обновлено!")
        await show_channel_detail(message, session, channel_id)
        
    except Exception as e:
        logger.error(f"Failed to update channel image: {e}")
        await message.answer("❌ Ошибка сохранения")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 АКТИВАЦИЯ/ДЕАКТИВАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:channels:activate:"))
async def callback_channel_activate(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Активация канала."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    channel_id = int(callback.data.split(":")[-1])
    
    try:
        await ChannelCRUD.update(session, channel_id, is_active=True)
        await callback.answer("✅ Канал активирован")
        await show_channel_detail(callback.message, session, channel_id)
        
    except Exception as e:
        logger.error(f"Failed to activate channel: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin:channels:deactivate:"))
async def callback_channel_deactivate(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Деактивация канала."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    channel_id = int(callback.data.split(":")[-1])
    
    try:
        await ChannelCRUD.update(session, channel_id, is_active=False)
        await callback.answer("✅ Канал деактивирован")
        await show_channel_detail(callback.message, session, channel_id)
        
    except Exception as e:
        logger.error(f"Failed to deactivate channel: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎁 ПРОБНЫЙ ПЕРИОД
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:channels:trial:"))
async def callback_channel_trial(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Управление пробным периодом."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    
    if len(parts) == 4:
        # admin:channels:trial:{channel_id} - показать меню
        channel_id = int(parts[3])
        channel = await ChannelCRUD.get_by_id(session, channel_id)
        
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return
        
        await callback.answer()
        
        text = f"""
🎁 <b>Пробный период: {channel.name_ru}</b>

━━━━━━━━━━━━━━━━━━━━━━
Статус: <b>{'✅ Включён' if channel.trial_enabled else '❌ Выключен'}</b>
Дней: <b>{channel.trial_days}</b>
━━━━━━━━━━━━━━━━━━━━━━

Пробный период позволяет пользователям
получить бесплатный доступ один раз.
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_channel_trial_keyboard(
                channel_id,
                channel.trial_enabled,
                channel.trial_days
            ),
            parse_mode="HTML"
        )
        
    elif parts[3] == "toggle":
        # Переключение триала
        channel_id = int(parts[4])
        channel = await ChannelCRUD.get_by_id(session, channel_id)
        
        new_status = not channel.trial_enabled
        await ChannelCRUD.update(session, channel_id, trial_enabled=new_status)
        
        status_text = "включён" if new_status else "выключен"
        await callback.answer(f"✅ Пробный период {status_text}")
        
        # Обновляем меню
        await callback_channel_trial(callback, session, state)
        
    elif parts[3] == "days":
        # Изменение количества дней
        channel_id = int(parts[4])
        await state.set_state(TrialSettingsState.waiting_days)
        await state.update_data(channel_id=channel_id)
        
        await callback.answer()
        await callback.message.edit_text(
            "📅 <b>Количество дней пробного периода</b>\n\n"
            "Введите число от 1 до 30:",
            reply_markup=get_back_button(f"admin:channels:trial:{channel_id}", "❌ Отмена"),
            parse_mode="HTML"
        )


@router.message(TrialSettingsState.waiting_days)
async def process_trial_days(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка количества дней триала."""
    if not await check_admin(message, session):
        return
    
    try:
        days = int(message.text.strip())
        if days < 1 or days > 30:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите число от 1 до 30")
        return
    
    data = await state.get_data()
    channel_id = data["channel_id"]
    
    await ChannelCRUD.update(session, channel_id, trial_days=days)
    await state.clear()
    
    await message.answer(f"✅ Пробный период установлен: {days} дней")
    
    # Возвращаемся к меню триала
    channel = await ChannelCRUD.get_by_id(session, channel_id)
    
    text = f"""
🎁 <b>Пробный период: {channel.name_ru}</b>

━━━━━━━━━━━━━━━━━━━━━━
Статус: <b>{'✅ Включён' if channel.trial_enabled else '❌ Выключен'}</b>
Дней: <b>{channel.trial_days}</b>
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.answer(
        text,
        reply_markup=get_channel_trial_keyboard(
            channel_id,
            channel.trial_enabled,
            channel.trial_days
        ),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🗑️ УДАЛЕНИЕ КАНАЛА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:channels:delete:"))
async def callback_channel_delete(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Запрос подтверждения удаления канала."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    channel_id = int(callback.data.split(":")[-1])
    channel = await ChannelCRUD.get_by_id(session, channel_id)
    
    if not channel:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(ChannelEditState.confirm_delete)
    await state.update_data(channel_id=channel_id)
    
    # Проверяем активные подписки
    active_subs = await SubscriptionCRUD.count_active_by_channel(session, channel_id)
    
    warning = ""
    if active_subs > 0:
        warning = f"\n\n⚠️ <b>ВНИМАНИЕ!</b> У канала {active_subs} активных подписок!"
    
    text = f"""
🗑️ <b>Удаление канала</b>

━━━━━━━━━━━━━━━━━━━━━━
Канал: <b>{channel.name_ru}</b>
━━━━━━━━━━━━━━━━━━━━━━
{warning}
Вы уверены, что хотите удалить этот канал?

<b>Это действие нельзя отменить!</b>
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_cancel_keyboard(
            f"admin:channels:delete:confirm:{channel_id}",
            f"admin:channels:view:{channel_id}",
            "🗑️ Да, удалить",
            "❌ Нет, отмена"
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:channels:delete:confirm:"))
async def confirm_channel_delete(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Подтверждение удаления канала."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    channel_id = int(callback.data.split(":")[-1])
    await state.clear()
    
    try:
        channel = await ChannelCRUD.get_by_id(session, channel_id)
        channel_name = channel.name_ru if channel else "Unknown"
        
        await ChannelCRUD.delete(session, channel_id)
        
        await callback.answer("✅ Канал удалён")
        
        logger.warning(
            f"Channel deleted: id={channel_id}, name={channel_name}, "
            f"admin_id={callback.from_user.id}"
        )
        
        # Возвращаемся к списку
        await show_channels_list(callback.message, session, edit=True)
        
    except Exception as e:
        logger.error(f"Failed to delete channel: {e}")
        await callback.answer("❌ Ошибка удаления", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 🔢 ИЗМЕНЕНИЕ ПОРЯДКА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:channels:order")
async def callback_channels_order(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Меню изменения порядка каналов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    channels = await ChannelCRUD.get_all(session, order_by="sort_order")
    
    if len(channels) < 2:
        await callback.message.edit_text(
            "ℹ️ Для изменения порядка нужно минимум 2 канала.",
            reply_markup=get_back_button("admin:channels")
        )
        return
    
    channels_data = [{"id": c.id, "name_ru": c.name_ru} for c in channels]
    
    text = """
🔢 <b>Изменение порядка каналов</b>

━━━━━━━━━━━━━━━━━━━━━━
Выберите канал, который хотите переместить:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_channel_order_keyboard(channels_data),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:channels:order:select:"))
async def callback_channel_order_select(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Выбор канала для перемещения."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    channel_id = int(callback.data.split(":")[-1])
    await callback.answer()
    
    channels = await ChannelCRUD.get_all(session, order_by="sort_order")
    current_pos = next(
        (i + 1 for i, c in enumerate(channels) if c.id == channel_id),
        1
    )
    
    channel = await ChannelCRUD.get_by_id(session, channel_id)
    
    text = f"""
🔢 <b>Перемещение канала</b>

━━━━━━━━━━━━━━━━━━━━━━
Канал: <b>{channel.name_ru}</b>
Текущая позиция: <b>{current_pos}</b>
━━━━━━━━━━━━━━━━━━━━━━

Выберите новую позицию:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_channel_position_keyboard(
            channel_id,
            current_pos,
            len(channels)
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:channels:order:move:"))
async def callback_channel_order_move(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Перемещение канала на новую позицию."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    channel_id = int(parts[4])
    new_position = int(parts[5])
    
    try:
        channels = await ChannelCRUD.get_all(session, order_by="sort_order")
        channel_ids = [c.id for c in channels]
        
        # Находим текущую позицию
        current_index = channel_ids.index(channel_id)
        new_index = new_position - 1
        
        # Перемещаем
        channel_ids.pop(current_index)
        channel_ids.insert(new_index, channel_id)
        
        # Обновляем sort_order для всех
        for i, cid in enumerate(channel_ids):
            await ChannelCRUD.update(session, cid, sort_order=i + 1)
        
        await callback.answer(f"✅ Канал перемещён на позицию {new_position}")
        
        # Возвращаемся к меню порядка
        channels = await ChannelCRUD.get_all(session, order_by="sort_order")
        channels_data = [{"id": c.id, "name_ru": c.name_ru} for c in channels]
        
        text = """
🔢 <b>Изменение порядка каналов</b>

━━━━━━━━━━━━━━━━━━━━━━
✅ Порядок обновлён!

Выберите канал для перемещения
или нажмите «Готово»:
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_channel_order_keyboard(channels_data),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Failed to reorder channels: {e}")
        await callback.answer("❌ Ошибка перемещения", show_alert=True)


@router.callback_query(F.data == "admin:channels:order:save")
async def callback_channels_order_save(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Завершение изменения порядка."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer("✅ Порядок сохранён")
    await show_channels_list(callback.message, session, edit=True)
