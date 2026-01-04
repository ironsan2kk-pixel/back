"""
═══════════════════════════════════════════════════════════════════════════════
💰 УПРАВЛЕНИЕ ТАРИФАМИ
═══════════════════════════════════════════════════════════════════════════════
Полное управление тарифами для каналов и пакетов.

Функционал:
- Просмотр тарифов по каналам/пакетам
- Добавление тарифа (пресеты и кастом)
- Редактирование цены и длительности
- Применение шаблонов тарифов
- Активация/деактивация
- Удаление тарифов
═══════════════════════════════════════════════════════════════════════════════
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Optional, List
import logging

from database.crud import PricingCRUD, ChannelCRUD, PackageCRUD
from keyboards.admin_kb import (
    get_pricing_menu,
    get_pricing_list_keyboard,
    get_pricing_detail_keyboard,
    get_pricing_add_target_keyboard,
    get_duration_presets_keyboard,
    get_price_presets_keyboard,
    get_pricing_templates_keyboard,
    get_confirm_cancel_keyboard,
    get_back_button,
    build_list_keyboard,
)
from states.admin_states import PricingAddState, PricingEditState
from handlers.admin.main import check_admin

logger = logging.getLogger(__name__)

router = Router(name="admin_pricing")


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 СПИСКИ ТАРИФОВ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:pricing:channels")
async def callback_pricing_channels(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Список каналов для просмотра тарифов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    channels = await ChannelCRUD.get_all(session)
    
    if not channels:
        await callback.message.edit_text(
            "📢 Каналов пока нет.\n\nСначала добавьте каналы.",
            reply_markup=get_back_button("admin:pricing")
        )
        return
    
    text = """
💰 <b>Тарифы каналов</b>

━━━━━━━━━━━━━━━━━━━━━━
Выберите канал для просмотра
и редактирования тарифов:
"""
    
    channels_data = [{"id": c.id, "name_ru": c.name_ru, "is_active": c.is_active} for c in channels]
    
    keyboard = build_list_keyboard(
        items=channels_data,
        callback_prefix="admin:pricing:channel",
        back_callback="admin:pricing"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin:pricing:packages")
async def callback_pricing_packages(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Список пакетов для просмотра тарифов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    packages = await PackageCRUD.get_all(session)
    
    if not packages:
        await callback.message.edit_text(
            "📦 Пакетов пока нет.\n\nСначала создайте пакеты.",
            reply_markup=get_back_button("admin:pricing")
        )
        return
    
    text = """
💰 <b>Тарифы пакетов</b>

━━━━━━━━━━━━━━━━━━━━━━
Выберите пакет для просмотра
и редактирования тарифов:
"""
    
    packages_data = [{"id": p.id, "name_ru": p.name_ru, "is_active": p.is_active} for p in packages]
    
    keyboard = build_list_keyboard(
        items=packages_data,
        callback_prefix="admin:pricing:package",
        back_callback="admin:pricing"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:pricing:channel:view:"))
async def callback_pricing_channel_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Тарифы конкретного канала."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    channel_id = int(callback.data.split(":")[-1])
    await callback.answer()
    await show_target_pricings(callback.message, session, "channel", channel_id)


@router.callback_query(F.data.startswith("admin:pricing:package:view:"))
async def callback_pricing_package_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Тарифы конкретного пакета."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    package_id = int(callback.data.split(":")[-1])
    await callback.answer()
    await show_target_pricings(callback.message, session, "package", package_id)


async def show_target_pricings(
    message: Message,
    session: AsyncSession,
    target_type: str,
    target_id: int,
    page: int = 0
):
    """Показать тарифы для канала/пакета."""
    # Получаем информацию о цели
    if target_type == "channel":
        target = await ChannelCRUD.get_by_id(session, target_id)
        target_name = target.name_ru if target else "Канал"
        icon = "📢"
    else:
        target = await PackageCRUD.get_by_id(session, target_id)
        target_name = target.name_ru if target else "Пакет"
        icon = "📦"
    
    if not target:
        await message.edit_text(
            "❌ Объект не найден.",
            reply_markup=get_back_button("admin:pricing")
        )
        return
    
    # Получаем тарифы
    pricings = await PricingCRUD.get_by_target(session, target_type, target_id)
    
    # Преобразуем в список словарей
    pricings_data = []
    for p in pricings:
        pricings_data.append({
            "id": p.id,
            "duration_days": p.duration_days,
            "price_usdt": float(p.price_usdt),
            "is_active": p.is_active,
        })
    
    # Сортируем по длительности
    pricings_data.sort(key=lambda x: (x["duration_days"] if x["duration_days"] > 0 else 9999))
    
    if not pricings_data:
        text = f"""
💰 <b>Тарифы: {icon} {target_name}</b>

━━━━━━━━━━━━━━━━━━━━━━
📭 Тарифов пока нет.

Добавьте тарифы, чтобы пользователи
могли покупать подписки.
"""
    else:
        # Формируем список тарифов
        tariffs_text = ""
        for p in pricings_data:
            status = "✅" if p["is_active"] else "❌"
            duration = format_duration(p["duration_days"])
            tariffs_text += f"\n{status} {duration} — <b>${p['price_usdt']}</b>"
        
        text = f"""
💰 <b>Тарифы: {icon} {target_name}</b>

━━━━━━━━━━━━━━━━━━━━━━
Всего тарифов: <b>{len(pricings_data)}</b>
{tariffs_text}
━━━━━━━━━━━━━━━━━━━━━━

Выберите тариф для редактирования:
"""
    
    keyboard = get_pricing_list_keyboard(
        pricings_data,
        target_type,
        target_id,
        page
    )
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


def format_duration(days: int) -> str:
    """Форматирование длительности."""
    if days == 0:
        return "♾️ Навсегда"
    elif days >= 365:
        years = days // 365
        return f"{years} год" if years == 1 else f"{years} лет"
    elif days >= 30:
        months = days // 30
        if months == 1:
            return "1 месяц"
        elif months < 5:
            return f"{months} месяца"
        else:
            return f"{months} месяцев"
    elif days == 7:
        return "1 неделя"
    elif days == 14:
        return "2 недели"
    else:
        return f"{days} дней"


# ═══════════════════════════════════════════════════════════════════════════════
# 👁️ ПРОСМОТР ТАРИФА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:pricing:view:"))
async def callback_pricing_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Просмотр конкретного тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    pricing_id = int(callback.data.split(":")[-1])
    await callback.answer()
    await show_pricing_detail(callback.message, session, pricing_id)


async def show_pricing_detail(
    message: Message,
    session: AsyncSession,
    pricing_id: int
):
    """Детальная информация о тарифе."""
    pricing = await PricingCRUD.get_by_id(session, pricing_id)
    
    if not pricing:
        await message.edit_text(
            "❌ Тариф не найден.",
            reply_markup=get_back_button("admin:pricing")
        )
        return
    
    # Получаем информацию о цели
    if pricing.channel_id:
        target = await ChannelCRUD.get_by_id(session, pricing.channel_id)
        target_name = f"📢 {target.name_ru}" if target else "Канал"
        target_type = "channel"
        target_id = pricing.channel_id
    else:
        target = await PackageCRUD.get_by_id(session, pricing.package_id)
        target_name = f"📦 {target.name_ru}" if target else "Пакет"
        target_type = "package"
        target_id = pricing.package_id
    
    status = "✅ Активен" if pricing.is_active else "❌ Неактивен"
    duration = format_duration(pricing.duration_days)
    
    text = f"""
💰 <b>Тариф #{pricing.id}</b>

━━━━━━━━━━━━━━━━━━━━━━
📌 <b>Основная информация</b>
━━━━━━━━━━━━━━━━━━━━━━

🎯 Для: <b>{target_name}</b>
📅 Длительность: <b>{duration}</b>
💵 Цена: <b>${pricing.price_usdt} USDT</b>
📍 Статус: <b>{status}</b>

━━━━━━━━━━━━━━━━━━━━━━
🏷️ <b>Метки (опционально)</b>
━━━━━━━━━━━━━━━━━━━━━━

🇷🇺 RU: {pricing.label_ru or '—'}
🇬🇧 EN: {pricing.label_en or '—'}

━━━━━━━━━━━━━━━━━━━━━━
Выберите действие:
"""
    
    await message.edit_text(
        text,
        reply_markup=get_pricing_detail_keyboard(pricing_id, pricing.is_active),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:pricing:back:"))
async def callback_pricing_back(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Возврат к списку тарифов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    pricing_id = int(callback.data.split(":")[-1])
    pricing = await PricingCRUD.get_by_id(session, pricing_id)
    
    if not pricing:
        await callback.answer()
        await callback.message.edit_text(
            "❌ Тариф не найден.",
            reply_markup=get_back_button("admin:pricing")
        )
        return
    
    await callback.answer()
    
    if pricing.channel_id:
        await show_target_pricings(callback.message, session, "channel", pricing.channel_id)
    else:
        await show_target_pricings(callback.message, session, "package", pricing.package_id)


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ ДОБАВЛЕНИЕ ТАРИФА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:pricing:add")
async def callback_pricing_add_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Начало добавления тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    text = """
➕ <b>Добавление тарифа</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>Шаг 1:</b> Выберите тип
━━━━━━━━━━━━━━━━━━━━━━

Для чего создаём тариф?
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pricing_add_target_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:pricing:add:select:"))
async def callback_pricing_add_select_target(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Выбор типа цели (канал/пакет)."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    target_type = callback.data.split(":")[-1]  # channel или package
    await callback.answer()
    
    # Показываем список для выбора
    if target_type == "channel":
        items = await ChannelCRUD.get_all(session, is_active=True)
        icon = "📢"
        empty_text = "Нет активных каналов"
    else:
        items = await PackageCRUD.get_all(session)
        items = [p for p in items if p.is_active]
        icon = "📦"
        empty_text = "Нет активных пакетов"
    
    if not items:
        await callback.message.edit_text(
            f"❌ {empty_text}",
            reply_markup=get_back_button("admin:pricing:add")
        )
        return
    
    text = f"""
➕ <b>Добавление тарифа</b>

━━━━━━━━━━━━━━━━━━━━━━
<b>Шаг 2:</b> Выберите {icon}
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    items_data = [{"id": i.id, "name_ru": i.name_ru} for i in items]
    
    keyboard = build_list_keyboard(
        items=items_data,
        callback_prefix=f"admin:pricing:add:{target_type}",
        status_field=None,
        back_callback="admin:pricing:add"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.regexp(r"admin:pricing:add:(channel|package):view:(\d+)"))
async def callback_pricing_add_target_selected(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Выбран конкретный канал/пакет."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    target_type = parts[3]  # channel или package
    target_id = int(parts[5])
    
    await callback.answer()
    await state.update_data(target_type=target_type, target_id=target_id)
    
    # Получаем название
    if target_type == "channel":
        target = await ChannelCRUD.get_by_id(session, target_id)
    else:
        target = await PackageCRUD.get_by_id(session, target_id)
    
    target_name = target.name_ru if target else "—"
    
    text = f"""
➕ <b>Добавление тарифа</b>

━━━━━━━━━━━━━━━━━━━━━━
🎯 Для: <b>{target_name}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 3:</b> Выберите длительность
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_duration_presets_keyboard(target_type, target_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:pricing:add:duration:"))
async def callback_pricing_add_duration(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Выбор длительности тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    
    if parts[4] == "custom":
        # Кастомная длительность
        target_type = parts[5]
        target_id = int(parts[6])
        
        await callback.answer()
        await state.set_state(PricingAddState.waiting_duration)
        await state.update_data(target_type=target_type, target_id=target_id)
        
        await callback.message.edit_text(
            "📅 <b>Длительность подписки</b>\n\n"
            "Введите количество дней (1-365)\n"
            "или 0 для бессрочной подписки:",
            reply_markup=get_back_button(f"admin:pricing:add:{target_type}:view:{target_id}", "❌ Отмена"),
            parse_mode="HTML"
        )
        return
    
    # Пресет длительности
    target_type = parts[4]
    target_id = int(parts[5])
    duration = int(parts[6])
    
    await callback.answer()
    await state.update_data(target_type=target_type, target_id=target_id, duration=duration)
    
    # Показываем выбор цены
    duration_text = format_duration(duration)
    
    text = f"""
➕ <b>Добавление тарифа</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 Длительность: <b>{duration_text}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 4:</b> Выберите цену (USDT)
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_price_presets_keyboard(target_type, target_id, duration),
        parse_mode="HTML"
    )


@router.message(PricingAddState.waiting_duration)
async def process_pricing_duration(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка кастомной длительности."""
    if not await check_admin(message, session):
        return
    
    try:
        duration = int(message.text.strip())
        if duration < 0 or duration > 365:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите число от 0 до 365")
        return
    
    data = await state.get_data()
    target_type = data["target_type"]
    target_id = data["target_id"]
    
    await state.update_data(duration=duration)
    await state.set_state(PricingAddState.waiting_price)
    
    duration_text = format_duration(duration)
    
    text = f"""
➕ <b>Добавление тарифа</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 Длительность: <b>{duration_text}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Шаг 4:</b> Выберите цену (USDT)
"""
    
    await message.answer(
        text,
        reply_markup=get_price_presets_keyboard(target_type, target_id, duration),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:pricing:add:price:"))
async def callback_pricing_add_price(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Выбор цены тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    
    if parts[4] == "custom":
        # Кастомная цена
        target_type = parts[5]
        target_id = int(parts[6])
        duration = int(parts[7])
        
        await callback.answer()
        await state.set_state(PricingAddState.waiting_price)
        await state.update_data(target_type=target_type, target_id=target_id, duration=duration)
        
        await callback.message.edit_text(
            "💵 <b>Цена подписки</b>\n\n"
            "Введите цену в USDT (например: 15 или 9.99):",
            reply_markup=get_back_button(f"admin:pricing:add:{target_type}:view:{target_id}", "❌ Отмена"),
            parse_mode="HTML"
        )
        return
    
    # Пресет цены
    target_type = parts[4]
    target_id = int(parts[5])
    duration = int(parts[6])
    price = Decimal(parts[7])
    
    await callback.answer()
    
    # Создаём тариф
    await create_pricing(callback.message, session, state, target_type, target_id, duration, price)


@router.message(PricingAddState.waiting_price)
async def process_pricing_price(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка кастомной цены."""
    if not await check_admin(message, session):
        return
    
    try:
        price = Decimal(message.text.strip().replace(",", "."))
        if price <= 0 or price > 10000:
            raise ValueError()
    except:
        await message.answer("❌ Введите корректную цену (0.01 - 10000)")
        return
    
    data = await state.get_data()
    target_type = data["target_type"]
    target_id = data["target_id"]
    duration = data["duration"]
    
    await create_pricing(message, session, state, target_type, target_id, duration, price)


async def create_pricing(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    target_type: str,
    target_id: int,
    duration: int,
    price: Decimal
):
    """Создание тарифа."""
    await state.clear()
    
    try:
        # Подготавливаем данные
        pricing_data = {
            "duration_days": duration,
            "price_usdt": price,
            "is_active": True,
        }
        
        if target_type == "channel":
            pricing_data["channel_id"] = target_id
        else:
            pricing_data["package_id"] = target_id
        
        # Проверяем, нет ли уже такого тарифа
        existing = await PricingCRUD.get_by_target_and_duration(
            session, target_type, target_id, duration
        )
        
        if existing:
            await message.answer(
                f"⚠️ Тариф на {format_duration(duration)} уже существует.\n"
                "Отредактируйте существующий тариф.",
                reply_markup=get_back_button(f"admin:pricing:{target_type}:view:{target_id}")
            )
            return
        
        # Создаём
        pricing = await PricingCRUD.create(session, **pricing_data)
        
        duration_text = format_duration(duration)
        
        await message.answer(
            f"✅ <b>Тариф создан!</b>\n\n"
            f"📅 Длительность: {duration_text}\n"
            f"💵 Цена: ${price} USDT",
            reply_markup=get_back_button(f"admin:pricing:view:{pricing.id}", "👁️ Просмотреть"),
            parse_mode="HTML"
        )
        
        logger.info(
            f"Pricing created: id={pricing.id}, {target_type}={target_id}, "
            f"duration={duration}, price={price}"
        )
        
    except Exception as e:
        logger.error(f"Failed to create pricing: {e}")
        await message.answer(
            f"❌ Ошибка создания тарифа: {str(e)}",
            reply_markup=get_back_button("admin:pricing")
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ✏️ РЕДАКТИРОВАНИЕ ТАРИФА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:pricing:edit:"))
async def callback_pricing_edit(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Редактирование поля тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    pricing_id = int(parts[3])
    field = parts[4]
    
    pricing = await PricingCRUD.get_by_id(session, pricing_id)
    if not pricing:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(PricingEditState.waiting_new_value)
    await state.update_data(pricing_id=pricing_id, field=field)
    
    field_info = {
        "price": ("💵 Цена (USDT)", f"${pricing.price_usdt}", "Введите новую цену:"),
        "days": ("📅 Длительность (дни)", format_duration(pricing.duration_days), "Введите количество дней (0 = навсегда):"),
        "label_ru": ("🇷🇺 Метка RU", pricing.label_ru or "—", "Введите метку на русском:"),
        "label_en": ("🇬🇧 Метка EN", pricing.label_en or "—", "Введите метку на английском:"),
    }
    
    label, current, prompt = field_info.get(field, ("Поле", "—", "Введите значение:"))
    
    text = f"""
✏️ <b>Редактирование: {label}</b>

━━━━━━━━━━━━━━━━━━━━━━
Текущее значение: <b>{current}</b>
━━━━━━━━━━━━━━━━━━━━━━

{prompt}
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_button(f"admin:pricing:view:{pricing_id}", "❌ Отмена"),
        parse_mode="HTML"
    )


@router.message(PricingEditState.waiting_new_value)
async def process_pricing_edit_value(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """Обработка нового значения поля тарифа."""
    if not await check_admin(message, session):
        return
    
    data = await state.get_data()
    pricing_id = data["pricing_id"]
    field = data["field"]
    value = message.text.strip()
    
    try:
        if field == "price":
            new_value = Decimal(value.replace(",", "."))
            if new_value <= 0 or new_value > 10000:
                raise ValueError("Invalid price")
            await PricingCRUD.update(session, pricing_id, price_usdt=new_value)
            
        elif field == "days":
            new_value = int(value)
            if new_value < 0 or new_value > 365:
                raise ValueError("Invalid days")
            await PricingCRUD.update(session, pricing_id, duration_days=new_value)
            
        elif field == "label_ru":
            await PricingCRUD.update(session, pricing_id, label_ru=value if value != "-" else None)
            
        elif field == "label_en":
            await PricingCRUD.update(session, pricing_id, label_en=value if value != "-" else None)
        
        await state.clear()
        await message.answer("✅ Сохранено!")
        await show_pricing_detail(message, session, pricing_id)
        
    except ValueError as e:
        await message.answer(f"❌ Некорректное значение: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update pricing: {e}")
        await message.answer("❌ Ошибка сохранения")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 АКТИВАЦИЯ/ДЕАКТИВАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:pricing:activate:"))
async def callback_pricing_activate(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Активация тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    pricing_id = int(callback.data.split(":")[-1])
    
    await PricingCRUD.update(session, pricing_id, is_active=True)
    await callback.answer("✅ Тариф активирован")
    await show_pricing_detail(callback.message, session, pricing_id)


@router.callback_query(F.data.startswith("admin:pricing:deactivate:"))
async def callback_pricing_deactivate(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Деактивация тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    pricing_id = int(callback.data.split(":")[-1])
    
    await PricingCRUD.update(session, pricing_id, is_active=False)
    await callback.answer("✅ Тариф деактивирован")
    await show_pricing_detail(callback.message, session, pricing_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 🗑️ УДАЛЕНИЕ ТАРИФА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:pricing:delete:"))
async def callback_pricing_delete(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Удаление тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    pricing_id = int(callback.data.split(":")[-1])
    pricing = await PricingCRUD.get_by_id(session, pricing_id)
    
    if not pricing:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    await callback.answer()
    
    # Определяем куда вернуться
    if pricing.channel_id:
        back_callback = f"admin:pricing:channel:view:{pricing.channel_id}"
    else:
        back_callback = f"admin:pricing:package:view:{pricing.package_id}"
    
    duration_text = format_duration(pricing.duration_days)
    
    text = f"""
🗑️ <b>Удаление тарифа</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 {duration_text} — ${pricing.price_usdt}
━━━━━━━━━━━━━━━━━━━━━━

Вы уверены, что хотите удалить этот тариф?
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_cancel_keyboard(
            f"admin:pricing:delete:confirm:{pricing_id}",
            f"admin:pricing:view:{pricing_id}",
            "🗑️ Удалить",
            "❌ Отмена"
        ),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:pricing:delete:confirm:"))
async def confirm_pricing_delete(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Подтверждение удаления тарифа."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    pricing_id = int(callback.data.split(":")[-1])
    pricing = await PricingCRUD.get_by_id(session, pricing_id)
    
    if not pricing:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return
    
    # Запоминаем куда вернуться
    if pricing.channel_id:
        target_type = "channel"
        target_id = pricing.channel_id
    else:
        target_type = "package"
        target_id = pricing.package_id
    
    try:
        await PricingCRUD.delete(session, pricing_id)
        await callback.answer("✅ Тариф удалён")
        
        logger.info(f"Pricing deleted: id={pricing_id}, admin_id={callback.from_user.id}")
        
        await show_target_pricings(callback.message, session, target_type, target_id)
        
    except Exception as e:
        logger.error(f"Failed to delete pricing: {e}")
        await callback.answer("❌ Ошибка удаления", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ШАБЛОНЫ ТАРИФОВ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:pricing:templates")
async def callback_pricing_templates(
    callback: CallbackQuery,
    session: AsyncSession
):
    """Меню шаблонов тарифов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    text = """
📋 <b>Шаблоны тарифов</b>

━━━━━━━━━━━━━━━━━━━━━━
Быстрое создание набора тарифов
для канала или пакета.
━━━━━━━━━━━━━━━━━━━━━━

<b>Стандартный:</b>
7 дн. / 30 дн. / 90 дн. / 365 дн.

<b>Премиум:</b>
30 дн. / 90 дн. / 180 дн. / 365 дн. / ♾️

<b>Простой:</b>
30 дн. / 365 дн.

━━━━━━━━━━━━━━━━━━━━━━
Выберите шаблон:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pricing_templates_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:pricing:template:"))
async def callback_pricing_template_apply(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """Применение шаблона тарифов."""
    if not await check_admin(callback, session):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    template = callback.data.split(":")[-1]
    
    templates = {
        "standard": [7, 30, 90, 365],
        "premium": [30, 90, 180, 365, 0],
        "simple": [30, 365],
    }
    
    if template not in templates:
        await callback.answer("❌ Неизвестный шаблон", show_alert=True)
        return
    
    await callback.answer()
    await state.update_data(template_durations=templates[template])
    
    # Показываем выбор канала/пакета
    text = f"""
📋 <b>Применение шаблона</b>

━━━━━━━━━━━━━━━━━━━━━━
Шаблон: <b>{template.title()}</b>
Тарифы: {', '.join(format_duration(d) for d in templates[template])}
━━━━━━━━━━━━━━━━━━━━━━

Для чего применить шаблон?
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pricing_add_target_keyboard(),
        parse_mode="HTML"
    )
