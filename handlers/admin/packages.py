"""
═══════════════════════════════════════════════════════════════════════════════
📦 УПРАВЛЕНИЕ ПАКЕТАМИ КАНАЛОВ
═══════════════════════════════════════════════════════════════════════════════
Полное управление пакетами: создание, редактирование, каналы, скидки.

Функционал:
- Просмотр списка пакетов
- Создание нового пакета (визард)
- Редактирование полей пакета
- Управление каналами в пакете
- Настройка скидки
- Пробный период
- Активация/деактивация
- Удаление пакета
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Set
import logging

from database.crud import PackageCRUD, ChannelCRUD, SubscriptionCRUD
from keyboards.admin_kb import (
    get_packages_menu,
    get_packages_list_keyboard,
    get_package_detail_keyboard,
    get_package_channels_keyboard,
    get_discount_keyboard,
    get_confirm_cancel_keyboard,
    get_back_button,
    get_skip_button,
)
from states.admin_states import PackageAddState, PackageEditState
from handlers.admin.main import check_admin

logger = logging.getLogger(__name__)

router = Router(name="admin_packages")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 СПИСОК ПАКЕТОВ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:packages:list")
async def callback_packages_list(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Показать список всех пакетов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await show_packages_list(callback.message, session, page=0, edit=True)


@router.callback_query(F.data.startswith("admin:packages:list:"))
async def callback_packages_list_page(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Пагинация списка пакетов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    page = int(callback.data.split(":")[-1])
    await callback.answer()
    await show_packages_list(callback.message, session, page=page, edit=True)


async def show_packages_list(
    message: Message,
    session: AsyncSession,
    page: int = 0,
    edit: bool = False
):
    """Отображение списка пакетов."""
    packages = await PackageCRUD.get_all(session)
    
    # Преобразуем в список словарей
    packages_data = []
    for pkg in packages:
        channels = await PackageCRUD.get_channels(session, pkg.id)
        packages_data.append({
            "id": pkg.id,
            "name_ru": pkg.name_ru,
            "is_active": pkg.is_active,
            "channels": channels,
            "discount_percent": pkg.discount_percent,
        })
    
    if not packages_data:
        text = """
📦 <b>Пакеты каналов</b>

━━━━━━━━━━━━━━━━━━━━━━
📭 Пакетов пока нет.

Пакет — это набор каналов со скидкой.
Нажмите «Создать», чтобы добавить первый пакет.
"""
    else:
        text = f"""
📦 <b>Список пакетов</b>

━━━━━━━━━━━━━━━━━━━━━━
Всего: <b>{len(packages_data)}</b> пакетов

Формат: статус | название (каналов, скидка)
━━━━━━━━━━━━━━━━━━━━━━

Выберите пакет для управления:
"""
    
    keyboard = get_packages_list_keyboard(packages_data, page=page)
    
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
# 👁️ ПРОСМОТР ПАКЕТА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:packages:view:"))
async def callback_package_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Просмотр детальной информации о пакете."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    package_id = int(callback.data.split(":")[-1])
    await callback.answer()
    await show_package_detail(callback.message, session, package_id)


async def show_package_detail(
    message: Message,
    session: AsyncSession,
    package_id: int
):
    """Отображение детальной информации о пакете."""
    package = await PackageCRUD.get_by_id(session, package_id)
    
    if not package:
        await message.edit_text(
            "❌ Пакет не найден.",
            reply_markup=get_back_button("admin:packages:list")
        )
        return
    
    # Получаем каналы пакета
    channels = await PackageCRUD.get_channels(session, package_id)
    channels_text = "\n".join(
        f"   • {ch.name_ru}" for ch in channels
    ) if channels else "   Нет каналов"
    
    # Статистика
    subs_count = await SubscriptionCRUD.count_by_package(session, package_id)
    active_subs = await SubscriptionCRUD.count_active_by_package(session, package_id)
    
    # Статус
    status = "✅ Активен" if package.is_active else "❌ Неактивен"
    
    # Пробный период
    if package.trial_enabled:
        trial_text = f"✅ Включён ({package.trial_days} дн.)"
    else:
        trial_text = "❌ Выключен"
    
    text = f"""
📦 <b>Пакет: {package.name_ru}</b>

━━━━━━━━━━━━━━━━━━━━━━
📌 <b>Основная информация</b>
━━━━━━━━━━━━━━━━━━━━━━

🆔 ID: <code>{package.id}</code>
💸 Скидка: <b>{package.discount_percent}%</b>
📍 Статус: <b>{status}</b>

━━━━━━━━━━━━━━━━━━━━━━
📝 <b>Названия</b>
━━━━━━━━━━━━━━━━━━━━━━

🇷🇺 RU: {package.name_ru}
🇬🇧 EN: {package.name_en or '—'}

━━━━━━━━━━━━━━━━━━━━━━
📄 <b>Описания</b>
━━━━━━━━━━━━━━━━━━━━━━

🇷🇺 RU: {package.description_ru or '—'}
🇬🇧 EN: {package.description_en or '—'}

━━━━━━━━━━━━━━━━━━━━━━
📢 <b>Каналы в пакете ({len(channels)})</b>
━━━━━━━━━━━━━━━━━━━━━━

{channels_text}

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Статистика</b>
━━━━━━━━━━━━━━━━━━━━━━

👥 Всего подписок: <b>{subs_count}</b>
✅ Активных: <b>{active_subs}</b>
🎁 Пробный период: <b>{trial_text}</b>
📷 Изображение: {'✅ Есть' if package.image_file_id else '❌ Нет'}

━━━━━━━━━━━━━━━━━━━━━━
Выберите действие:
"""
    
    await message.edit_text(
        text,
        reply_markup=get_package_detail_keyboard(package_id, package.is_active),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ ПАКЕТА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:packages:add")
async def callback_package_add_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Начало создания пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    # Проверяем наличие каналов
    channels = await ChannelCRUD.get_all(session, is_active=True)
    if len(channels) < 2:
        await callback.answer(
            "⚠️ Для создания пакета нужно минимум 2 активных канала",
            show_alert=True
        )
        return
    
    await callback.answer()
    await state.set_state(PackageAddState.waiting_name_ru)
    
    text = """
➕ <b>Создание пакета</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>Шаг 1/6:</b> Название на русском
━━━━━━━━━━━━━━━━━━━━━━

Введите название пакета на русском языке.

<b>Пример:</b> Полный доступ, VIP-пакет, Все каналы
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_button("admin:packages", "❌ Отмена"),
        parse_mode="HTML"
    )


@router.message(PackageAddState.waiting_name_ru)
async def process_package_name_ru(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка названия пакета на русском."""
    if not await check_admin(message, session):
        return
    
    name_ru = message.text.strip()
    
    if len(name_ru) > 100:
        await message.answer("❌ Название слишком длинное (макс. 100 символов)")
        return
    
    await state.update_data(name_ru=name_ru)
    await state.set_state(PackageAddState.waiting_name_en)
    
    text = f"""
➕ <b>Создание пакета</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 Название RU: <b>{name_ru}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 2/6:</b> Название на английском

Введите название пакета на английском языке.
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [get_skip_button("admin:packages:add:skip:name_en")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:packages")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:packages:add:skip:name_en")
async def skip_package_name_en(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Пропуск английского названия пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    data = await state.get_data()
    await state.update_data(name_en=data.get("name_ru"))
    await state.set_state(PackageAddState.waiting_description_ru)
    
    await ask_package_description_ru(callback.message, data.get("name_ru"), data.get("name_ru"))


@router.message(PackageAddState.waiting_name_en)
async def process_package_name_en(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка названия пакета на английском."""
    if not await check_admin(message, session):
        return
    
    name_en = message.text.strip()
    
    if len(name_en) > 100:
        await message.answer("❌ Название слишком длинное (макс. 100 символов)")
        return
    
    data = await state.get_data()
    await state.update_data(name_en=name_en)
    await state.set_state(PackageAddState.waiting_description_ru)
    
    await ask_package_description_ru(message, data.get("name_ru"), name_en)


async def ask_package_description_ru(message: Message, name_ru: str, name_en: str):
    """Запрос описания пакета на русском."""
    text = f"""
➕ <b>Создание пакета</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 Название RU: <b>{name_ru}</b>
🇬🇧 Название EN: <b>{name_en}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 3/6:</b> Описание на русском

Введите описание пакета на русском языке.
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [get_skip_button("admin:packages:add:skip:desc_ru")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:packages")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:packages:add:skip:desc_ru")
async def skip_package_desc_ru(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Пропуск русского описания пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await state.update_data(description_ru=None, description_en=None)
    await state.set_state(PackageAddState.selecting_channels)
    
    data = await state.get_data()
    await show_channel_selection(callback.message, session, data, set())


@router.message(PackageAddState.waiting_description_ru)
async def process_package_desc_ru(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка описания пакета на русском."""
    if not await check_admin(message, session):
        return
    
    description_ru = message.text.strip()
    
    if len(description_ru) > 500:
        await message.answer("❌ Описание слишком длинное (макс. 500 символов)")
        return
    
    await state.update_data(description_ru=description_ru)
    await state.set_state(PackageAddState.waiting_description_en)
    
    data = await state.get_data()
    await ask_package_description_en(message, data)


async def ask_package_description_en(message: Message, data: dict):
    """Запрос описания пакета на английском."""
    text = f"""
➕ <b>Создание пакета</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 {data.get('name_ru')}
🇬🇧 {data.get('name_en')}
📝 Описание RU: {data.get('description_ru') or '—'}
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 4/6:</b> Описание на английском

Введите описание пакета на английском языке.
"""
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [get_skip_button("admin:packages:add:skip:desc_en")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:packages")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:packages:add:skip:desc_en")
async def skip_package_desc_en(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Пропуск английского описания пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await state.update_data(description_en=None)
    await state.set_state(PackageAddState.selecting_channels)
    
    data = await state.get_data()
    await show_channel_selection(callback.message, session, data, set())


@router.message(PackageAddState.waiting_description_en)
async def process_package_desc_en(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка описания пакета на английском."""
    if not await check_admin(message, session):
        return
    
    description_en = message.text.strip()
    
    if len(description_en) > 500:
        await message.answer("❌ Описание слишком длинное (макс. 500 символов)")
        return
    
    await state.update_data(description_en=description_en)
    await state.set_state(PackageAddState.selecting_channels)
    
    data = await state.get_data()
    await show_channel_selection(message, session, data, set())


async def show_channel_selection(
    message: Message,
    session: AsyncSession,
    data: dict,
    selected_ids: Set[int]
):
    """Показать выбор каналов для пакета."""
    channels = await ChannelCRUD.get_all(session, is_active=True)
    
    all_channels = [{"id": c.id, "name_ru": c.name_ru} for c in channels]
    
    selected_names = [c["name_ru"] for c in all_channels if c["id"] in selected_ids]
    selected_text = "\n".join(f"   ✅ {n}" for n in selected_names) if selected_names else "   Не выбрано"
    
    text = f"""
➕ <b>Создание пакета</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 {data.get('name_ru')}
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 5/6:</b> Выбор каналов

Выберите каналы, которые войдут в пакет.
Минимум 2 канала.

<b>Выбрано ({len(selected_ids)}):</b>
{selected_text}
"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    for channel in all_channels:
        if channel["id"] in selected_ids:
            text_btn = f"✅ {channel['name_ru']}"
            callback = f"admin:packages:add:ch:remove:{channel['id']}"
        else:
            text_btn = f"⬜ {channel['name_ru']}"
            callback = f"admin:packages:add:ch:add:{channel['id']}"
        builder.button(text=text_btn, callback_data=callback)
    
    builder.adjust(1)
    
    # Кнопка продолжить (если выбрано >= 2)
    if len(selected_ids) >= 2:
        builder.row(
            InlineKeyboardButton(text="✅ Продолжить", callback_data="admin:packages:add:ch:done")
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:packages")
    )
    
    await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:packages:add:ch:"))
async def callback_package_channel_toggle(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Добавление/удаление канала из выбора."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    action = parts[4]  # add, remove, done
    
    data = await state.get_data()
    selected_ids = set(data.get("selected_channels", []))
    
    if action == "add":
        channel_id = int(parts[5])
        selected_ids.add(channel_id)
        await callback.answer("✅ Добавлен")
    
    elif action == "remove":
        channel_id = int(parts[5])
        selected_ids.discard(channel_id)
        await callback.answer("❌ Убран")
    
    elif action == "done":
        if len(selected_ids) < 2:
            await callback.answer("⚠️ Выберите минимум 2 канала", show_alert=True)
            return
        
        await callback.answer()
        await state.update_data(selected_channels=list(selected_ids))
        await state.set_state(PackageAddState.waiting_discount)
        
        await ask_package_discount(callback.message, data, selected_ids)
        return
    
    await state.update_data(selected_channels=list(selected_ids))
    await show_channel_selection(callback.message, session, data, selected_ids)


async def ask_package_discount(message: Message, data: dict, selected_ids: Set[int]):
    """Запрос скидки пакета."""
    text = f"""
➕ <b>Создание пакета</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 {data.get('name_ru')}
📢 Каналов: <b>{len(selected_ids)}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 6/6:</b> Скидка пакета

Выберите размер скидки для пакета.
Скидка применяется к сумме цен всех каналов.

<b>Пример:</b>
Если каналы стоят $10 + $15 = $25,
то со скидкой 20% пакет будет стоить $20.
"""
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    
    discounts = [0, 5, 10, 15, 20, 25, 30]
    for d in discounts:
        builder.button(text=f"{d}%", callback_data=f"admin:packages:add:discount:{d}")
    
    builder.adjust(4)
    builder.row(
        InlineKeyboardButton(text="✏️ Своё значение", callback_data="admin:packages:add:discount:custom")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:packages")
    )
    
    await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:packages:add:discount:"))
async def callback_package_discount(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Выбор скидки пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    value = callback.data.split(":")[-1]
    
    if value == "custom":
        await callback.answer()
        text = """
💸 <b>Своё значение скидки</b>

Введите процент скидки (0-50):
"""
        await callback.message.edit_text(
            text,
            reply_markup=get_back_button("admin:packages:add", "❌ Отмена"),
            parse_mode="HTML"
        )
        # Остаёмся в том же состоянии, но обрабатываем текст
        return
    
    discount = int(value)
    await state.update_data(discount_percent=discount)
    
    await callback.answer()
    
    data = await state.get_data()
    await show_package_confirm(callback.message, session, data)


@router.message(PackageAddState.waiting_discount)
async def process_package_discount_custom(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка кастомной скидки."""
    if not await check_admin(message, session):
        return
    
    try:
        discount = int(message.text.strip())
        if discount < 0 or discount > 50:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите число от 0 до 50")
        return
    
    await state.update_data(discount_percent=discount)
    
    data = await state.get_data()
    await show_package_confirm(message, session, data)


async def show_package_confirm(message: Message, session: AsyncSession, data: dict):
    """Показ подтверждения создания пакета."""
    # Получаем названия выбранных каналов
    channel_ids = data.get("selected_channels", [])
    channels = []
    for cid in channel_ids:
        ch = await ChannelCRUD.get_by_id(session, cid)
        if ch:
            channels.append(ch.name_ru)
    
    channels_text = "\n".join(f"   • {n}" for n in channels)
    
    text = f"""
➕ <b>Подтверждение создания пакета</b>

━━━━━━━━━━━━━━━━━━━━━━
🇷🇺 <b>Русский:</b>
   • Название: {data.get('name_ru')}
   • Описание: {data.get('description_ru') or '—'}

🇬🇧 <b>English:</b>
   • Name: {data.get('name_en')}
   • Description: {data.get('description_en') or '—'}

📢 <b>Каналы ({len(channels)}):</b>
{channels_text}

💸 Скидка: <b>{data.get('discount_percent', 0)}%</b>
━━━━━━━━━━━━━━━━━━━━━━

Создать пакет?
"""
    
    await message.answer(
        text,
        reply_markup=get_confirm_cancel_keyboard(
            "admin:packages:add:confirm",
            "admin:packages"
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:packages:add:confirm")
async def confirm_package_add(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Подтверждение создания пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    await state.clear()
    
    try:
        # Создаём пакет
        package = await PackageCRUD.create(
            session,
            name_ru=data["name_ru"],
            name_en=data.get("name_en"),
            description_ru=data.get("description_ru"),
            description_en=data.get("description_en"),
            discount_percent=data.get("discount_percent", 0),
            is_active=True
        )
        
        # Добавляем каналы
        channel_ids = data.get("selected_channels", [])
        await PackageCRUD.set_channels(session, package.id, channel_ids)
        
        await callback.answer("✅ Пакет создан!")
        await show_package_detail(callback.message, session, package.id)
        
        logger.info(
            f"Package created: id={package.id}, name={package.name_ru}, "
            f"channels={len(channel_ids)}, admin_id={callback.from_user.id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to create package: {e}")
        await callback.answer("❌ Ошибка создания пакета", show_alert=True)
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_back_button("admin:packages")
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ✏️ РЕДАКТИРОВАНИЕ ПАКЕТА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:packages:edit:"))
async def callback_package_edit(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Редактирование поля пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    package_id = int(parts[3])
    field = parts[4]
    
    package = await PackageCRUD.get_by_id(session, package_id)
    if not package:
        await callback.answer("❌ Пакет не найден", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(PackageEditState.waiting_new_value)
    await state.update_data(package_id=package_id, field=field)
    
    field_labels = {
        "name_ru": ("🇷🇺 Название (RU)", package.name_ru),
        "name_en": ("🇬🇧 Название (EN)", package.name_en),
        "desc_ru": ("🇷🇺 Описание (RU)", package.description_ru),
        "desc_en": ("🇬🇧 Описание (EN)", package.description_en),
        "image": ("🖼️ Изображение", "Загружено" if package.image_file_id else "Нет"),
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
        await state.set_state(PackageEditState.waiting_image)
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
        reply_markup=get_back_button(f"admin:packages:view:{package_id}", "❌ Отмена"),
        parse_mode="HTML"
    )


@router.message(PackageEditState.waiting_new_value)
async def process_package_edit_value(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка нового значения поля пакета."""
    if not await check_admin(message, session):
        return
    
    data = await state.get_data()
    package_id = data["package_id"]
    field = data["field"]
    new_value = message.text.strip()
    
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
    
    if db_field.startswith("name") and len(new_value) > 100:
        await message.answer("❌ Название слишком длинное (макс. 100 символов)")
        return
    
    if db_field.startswith("description") and len(new_value) > 500:
        await message.answer("❌ Описание слишком длинное (макс. 500 символов)")
        return
    
    try:
        await PackageCRUD.update(session, package_id, **{db_field: new_value})
        await state.clear()
        await message.answer("✅ Сохранено!")
        await show_package_detail(message, session, package_id)
        
    except Exception as e:
        logger.error(f"Failed to update package: {e}")
        await message.answer("❌ Ошибка сохранения")


@router.message(PackageEditState.waiting_image, F.photo)
async def process_package_edit_image(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка нового изображения пакета."""
    if not await check_admin(message, session):
        return
    
    data = await state.get_data()
    package_id = data["package_id"]
    photo = message.photo[-1]
    
    try:
        await PackageCRUD.update(session, package_id, image_file_id=photo.file_id)
        await state.clear()
        await message.answer("✅ Изображение обновлено!")
        await show_package_detail(message, session, package_id)
        
    except Exception as e:
        logger.error(f"Failed to update package image: {e}")
        await message.answer("❌ Ошибка сохранения")


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 УПРАВЛЕНИЕ КАНАЛАМИ В ПАКЕТЕ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:packages:channels:"))
async def callback_package_channels(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Управление каналами пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    
    if len(parts) == 4:
        # admin:packages:channels:{package_id} - показать выбор
        package_id = int(parts[3])
        await callback.answer()
        await show_edit_package_channels(callback.message, session, package_id, state)
        
    elif parts[3] == "add":
        # Добавление канала
        package_id = int(parts[4])
        channel_id = int(parts[5])
        
        data = await state.get_data()
        selected = set(data.get("editing_channels", []))
        selected.add(channel_id)
        await state.update_data(editing_channels=list(selected))
        
        await callback.answer("✅ Добавлен")
        await show_edit_package_channels(callback.message, session, package_id, state)
        
    elif parts[3] == "remove":
        # Удаление канала
        package_id = int(parts[4])
        channel_id = int(parts[5])
        
        data = await state.get_data()
        selected = set(data.get("editing_channels", []))
        selected.discard(channel_id)
        await state.update_data(editing_channels=list(selected))
        
        await callback.answer("❌ Убран")
        await show_edit_package_channels(callback.message, session, package_id, state)
        
    elif parts[3] == "save":
        # Сохранение
        package_id = int(parts[4])
        data = await state.get_data()
        selected = data.get("editing_channels", [])
        
        if len(selected) < 2:
            await callback.answer("⚠️ Минимум 2 канала", show_alert=True)
            return
        
        await PackageCRUD.set_channels(session, package_id, selected)
        await state.clear()
        
        await callback.answer("✅ Каналы сохранены")
        await show_package_detail(callback.message, session, package_id)


async def show_edit_package_channels(
    message: Message,
    session: AsyncSession,
    package_id: int,
    state: FSMContext
):
    """Показать редактирование каналов пакета."""
    package = await PackageCRUD.get_by_id(session, package_id)
    
    # Получаем текущие каналы из состояния или из БД
    data = await state.get_data()
    
    if "editing_channels" not in data:
        current_channels = await PackageCRUD.get_channels(session, package_id)
        selected_ids = [c.id for c in current_channels]
        await state.update_data(editing_channels=selected_ids, package_id=package_id)
    else:
        selected_ids = data.get("editing_channels", [])
    
    # Все доступные каналы
    all_channels = await ChannelCRUD.get_all(session, is_active=True)
    all_channels_data = [{"id": c.id, "name_ru": c.name_ru} for c in all_channels]
    
    text = f"""
📢 <b>Каналы пакета: {package.name_ru}</b>

━━━━━━━━━━━━━━━━━━━━━━
Выбрано: <b>{len(selected_ids)}</b> каналов
(минимум 2)
━━━━━━━━━━━━━━━━━━━━━━

Выберите каналы:
"""
    
    keyboard = get_package_channels_keyboard(
        package_id,
        all_channels_data,
        selected_ids
    )
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
# 💸 НАСТРОЙКА СКИДКИ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:packages:discount:"))
async def callback_package_discount_edit(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Изменение скидки пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    
    if len(parts) == 4:
        # Показать меню скидки
        package_id = int(parts[3])
        package = await PackageCRUD.get_by_id(session, package_id)
        
        await callback.answer()
        
        text = f"""
💸 <b>Скидка пакета: {package.name_ru}</b>

━━━━━━━━━━━━━━━━━━━━━━
Текущая скидка: <b>{package.discount_percent}%</b>
━━━━━━━━━━━━━━━━━━━━━━

Выберите новую скидку:
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_discount_keyboard(package_id, package.discount_percent),
            parse_mode="HTML"
        )
        
    elif parts[3] == "set":
        # Установка скидки
        package_id = int(parts[4])
        discount = int(parts[5])
        
        await PackageCRUD.update(session, package_id, discount_percent=discount)
        await callback.answer(f"✅ Скидка установлена: {discount}%")
        await show_package_detail(callback.message, session, package_id)
        
    elif parts[3] == "custom":
        # Кастомная скидка
        package_id = int(parts[4])
        await state.update_data(package_id=package_id)
        
        await callback.answer()
        await callback.message.edit_text(
            "💸 Введите процент скидки (0-50):",
            reply_markup=get_back_button(f"admin:packages:view:{package_id}", "❌ Отмена"),
            parse_mode="HTML"
        )
        # Нужно создать отдельное состояние для этого


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 АКТИВАЦИЯ/ДЕАКТИВАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:packages:activate:"))
async def callback_package_activate(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Активация пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    package_id = int(callback.data.split(":")[-1])
    
    await PackageCRUD.update(session, package_id, is_active=True)
    await callback.answer("✅ Пакет активирован")
    await show_package_detail(callback.message, session, package_id)


@router.callback_query(F.data.startswith("admin:packages:deactivate:"))
async def callback_package_deactivate(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Деактивация пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    package_id = int(callback.data.split(":")[-1])
    
    await PackageCRUD.update(session, package_id, is_active=False)
    await callback.answer("✅ Пакет деактивирован")
    await show_package_detail(callback.message, session, package_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎁 ПРОБНЫЙ ПЕРИОД ПАКЕТА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:packages:trial:"))
async def callback_package_trial(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Управление пробным периодом пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    package_id = int(parts[3])
    
    package = await PackageCRUD.get_by_id(session, package_id)
    
    # Переключаем статус
    new_status = not package.trial_enabled
    await PackageCRUD.update(session, package_id, trial_enabled=new_status)
    
    status_text = "включён" if new_status else "выключен"
    await callback.answer(f"✅ Пробный период {status_text}")
    
    await show_package_detail(callback.message, session, package_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 🗑️ УДАЛЕНИЕ ПАКЕТА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:packages:delete:"))
async def callback_package_delete(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Удаление пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    
    if len(parts) == 4:
        # Запрос подтверждения
        package_id = int(parts[3])
        package = await PackageCRUD.get_by_id(session, package_id)
        
        if not package:
            await callback.answer("❌ Пакет не найден", show_alert=True)
            return
        
        active_subs = await SubscriptionCRUD.count_active_by_package(session, package_id)
        
        warning = ""
        if active_subs > 0:
            warning = f"\n\n⚠️ <b>ВНИМАНИЕ!</b> У пакета {active_subs} активных подписок!"
        
        await callback.answer()
        
        text = f"""
🗑️ <b>Удаление пакета</b>

━━━━━━━━━━━━━━━━━━━━━━
Пакет: <b>{package.name_ru}</b>
━━━━━━━━━━━━━━━━━━━━━━
{warning}
Вы уверены?

<b>Это действие нельзя отменить!</b>
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_confirm_cancel_keyboard(
                f"admin:packages:delete:confirm:{package_id}",
                f"admin:packages:view:{package_id}",
                "🗑️ Да, удалить",
                "❌ Нет"
            ),
            parse_mode="HTML"
        )
        
    elif parts[3] == "confirm":
        # Подтверждение удаления
        package_id = int(parts[4])
        
        try:
            package = await PackageCRUD.get_by_id(session, package_id)
            package_name = package.name_ru if package else "Unknown"
            
            await PackageCRUD.delete(session, package_id)
            
            await callback.answer("✅ Пакет удалён")
            
            logger.warning(
                f"Package deleted: id={package_id}, name={package_name}, "
                f"admin_id={callback.from_user.id}"
            )
            
            await show_packages_list(callback.message, session, edit=True)
            
        except Exception as e:
            logger.error(f"Failed to delete package: {e}")
            await callback.answer("❌ Ошибка удаления", show_alert=True)
