"""
═══════════════════════════════════════════════════════════════════════════════
🎟️ АДМИН-ПАНЕЛЬ — УПРАВЛЕНИЕ ПРОМОКОДАМИ
═══════════════════════════════════════════════════════════════════════════════
Полный CRUD промокодов:
- Просмотр списка с пагинацией и фильтрацией
- Создание (ручное/массовое генерирование)
- Редактирование (код, скидка, лимиты, срок)
- Удаление с подтверждением
- Статистика использования
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from keyboards.admin_kb import (
    get_promos_menu_keyboard,
    get_promo_list_keyboard,
    get_promo_detail_keyboard,
    get_promo_type_keyboard,
    get_promo_discount_type_keyboard,
    get_promo_target_keyboard,
    get_promo_channels_keyboard,
    get_promo_packages_keyboard,
    get_promo_edit_keyboard,
    get_confirm_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
)
from states.admin_states import PromoAdminState
from database.crud import PromoCRUD, ChannelCRUD, PackageCRUD, PromoUsageCRUD
from utils.i18n import get_text

logger = logging.getLogger(__name__)
router = Router(name="admin_promos")

# Символы для генерации промокодов
PROMO_CHARS = string.ascii_uppercase + string.digits
ITEMS_PER_PAGE = 8


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════════

def generate_promo_code(length: int = 8) -> str:
    """Генерация случайного промокода."""
    return ''.join(random.choices(PROMO_CHARS, k=length))


def generate_promo_codes(count: int, length: int = 8, prefix: str = "") -> List[str]:
    """Генерация нескольких уникальных промокодов."""
    codes = set()
    while len(codes) < count:
        code = prefix + generate_promo_code(length - len(prefix))
        codes.add(code.upper())
    return list(codes)


def format_promo_info(promo: dict) -> str:
    """Форматирование информации о промокоде для отображения."""
    # Определяем тип скидки
    if promo.get('discount_percent'):
        discount = f"{promo['discount_percent']}%"
    elif promo.get('discount_amount'):
        discount = f"${promo['discount_amount']}"
    elif promo.get('bonus_days'):
        discount = f"+{promo['bonus_days']} дней"
    else:
        discount = "—"
    
    # Статус
    if not promo.get('is_active', True):
        status = "❌ Неактивен"
    elif promo.get('expires_at') and promo['expires_at'] < datetime.utcnow():
        status = "⏰ Истёк"
    elif promo.get('max_uses') and promo.get('used_count', 0) >= promo['max_uses']:
        status = "🔒 Исчерпан"
    else:
        status = "✅ Активен"
    
    # Использование
    used = promo.get('used_count', 0)
    max_uses = promo.get('max_uses')
    usage = f"{used}/{max_uses}" if max_uses else f"{used}/∞"
    
    # Срок действия
    if promo.get('expires_at'):
        expires = promo['expires_at'].strftime('%d.%m.%Y')
    else:
        expires = "Бессрочно"
    
    # Цель промокода
    if promo.get('channel_id'):
        target = f"📢 Канал #{promo['channel_id']}"
    elif promo.get('package_id'):
        target = f"📦 Пакет #{promo['package_id']}"
    else:
        target = "🌐 Все"
    
    return (
        f"🎟️ <code>{promo['code']}</code>\n\n"
        f"📊 <b>Статус:</b> {status}\n"
        f"💰 <b>Скидка:</b> {discount}\n"
        f"🎯 <b>Цель:</b> {target}\n"
        f"📈 <b>Использовано:</b> {usage}\n"
        f"📅 <b>Истекает:</b> {expires}\n"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ГЛАВНОЕ МЕНЮ ПРОМОКОДОВ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:promos")
async def show_promos_menu(callback: CallbackQuery, state: FSMContext):
    """Главное меню управления промокодами."""
    await state.clear()
    
    # Получаем статистику
    total_promos = await PromoCRUD.count_all()
    active_promos = await PromoCRUD.count_active()
    used_today = await PromoUsageCRUD.count_today()
    total_usage = await PromoUsageCRUD.count_all()
    
    text = (
        "🎟️ <b>Управление промокодами</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ Всего промокодов: <b>{total_promos}</b>\n"
        f"├ Активных: <b>{active_promos}</b>\n"
        f"├ Использовано сегодня: <b>{used_today}</b>\n"
        f"└ Всего использований: <b>{total_usage}</b>\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promos_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 СПИСОК ПРОМОКОДОВ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:promos:list"))
async def show_promos_list(callback: CallbackQuery, state: FSMContext):
    """Список промокодов с пагинацией."""
    parts = callback.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    filter_type = parts[4] if len(parts) > 4 else "all"
    
    # Получаем промокоды в зависимости от фильтра
    if filter_type == "active":
        promos = await PromoCRUD.get_active(offset=page * ITEMS_PER_PAGE, limit=ITEMS_PER_PAGE)
        total = await PromoCRUD.count_active()
        title = "✅ Активные промокоды"
    elif filter_type == "expired":
        promos = await PromoCRUD.get_expired(offset=page * ITEMS_PER_PAGE, limit=ITEMS_PER_PAGE)
        total = await PromoCRUD.count_expired()
        title = "⏰ Истёкшие промокоды"
    elif filter_type == "used":
        promos = await PromoCRUD.get_fully_used(offset=page * ITEMS_PER_PAGE, limit=ITEMS_PER_PAGE)
        total = await PromoCRUD.count_fully_used()
        title = "🔒 Исчерпанные промокоды"
    else:
        promos = await PromoCRUD.get_all(offset=page * ITEMS_PER_PAGE, limit=ITEMS_PER_PAGE)
        total = await PromoCRUD.count_all()
        title = "📋 Все промокоды"
    
    if not promos:
        text = f"{title}\n\n📭 Промокоды не найдены"
    else:
        text = f"{title}\n\n"
        for promo in promos:
            # Статус иконка
            if not promo.is_active:
                icon = "❌"
            elif promo.expires_at and promo.expires_at < datetime.utcnow():
                icon = "⏰"
            elif promo.max_uses and promo.used_count >= promo.max_uses:
                icon = "🔒"
            else:
                icon = "✅"
            
            # Скидка
            if promo.discount_percent:
                discount = f"-{promo.discount_percent}%"
            elif promo.discount_amount:
                discount = f"-${promo.discount_amount}"
            elif promo.bonus_days:
                discount = f"+{promo.bonus_days}д"
            else:
                discount = "—"
            
            text += f"{icon} <code>{promo.code}</code> — {discount}\n"
    
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    text += f"\n📄 Страница {page + 1}/{max(1, total_pages)}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promo_list_keyboard(promos, page, total_pages, filter_type),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 ДЕТАЛИ ПРОМОКОДА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:promo:view:"))
async def show_promo_details(callback: CallbackQuery, state: FSMContext):
    """Просмотр детальной информации о промокоде."""
    promo_id = int(callback.data.split(":")[3])
    
    promo = await PromoCRUD.get_by_id(promo_id)
    if not promo:
        await callback.answer("❌ Промокод не найден", show_alert=True)
        return
    
    # Получаем дополнительную информацию
    recent_usages = await PromoUsageCRUD.get_by_promo(promo_id, limit=5)
    
    # Формируем текст
    text = format_promo_info({
        'code': promo.code,
        'discount_percent': promo.discount_percent,
        'discount_amount': promo.discount_amount,
        'bonus_days': promo.bonus_days,
        'is_active': promo.is_active,
        'expires_at': promo.expires_at,
        'max_uses': promo.max_uses,
        'used_count': promo.used_count,
        'channel_id': promo.channel_id,
        'package_id': promo.package_id,
    })
    
    # Добавляем историю использования
    if recent_usages:
        text += "\n📜 <b>Последние использования:</b>\n"
        for usage in recent_usages:
            used_at = usage.used_at.strftime('%d.%m %H:%M')
            text += f"├ {used_at} — User #{usage.user_id}\n"
    
    # Дата создания
    if promo.created_at:
        text += f"\n🕐 <b>Создан:</b> {promo.created_at.strftime('%d.%m.%Y %H:%M')}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promo_detail_keyboard(promo_id, promo.is_active),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ ПРОМОКОДА — ШАГ 1: ТИП СОЗДАНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:promos:add")
async def start_promo_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания промокода — выбор типа."""
    await state.clear()
    
    text = (
        "➕ <b>Создание промокода</b>\n\n"
        "Выберите способ создания:\n\n"
        "📝 <b>Ручной</b> — вы указываете код самостоятельно\n"
        "🎲 <b>Сгенерировать</b> — случайный код\n"
        "📦 <b>Массовая генерация</b> — несколько кодов сразу"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promo_type_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ — ШАГ 2A: РУЧНОЙ ВВОД КОДА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:promo:create:manual")
async def promo_manual_code(callback: CallbackQuery, state: FSMContext):
    """Ввод кода вручную."""
    await state.set_state(PromoAdminState.entering_code)
    await state.update_data(creation_type="manual")
    
    text = (
        "📝 <b>Введите код промокода</b>\n\n"
        "• Только латинские буквы и цифры\n"
        "• Длина: 4-20 символов\n"
        "• Пример: <code>SALE50</code>, <code>NEWYEAR2025</code>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard("admin:promos"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(StateFilter(PromoAdminState.entering_code))
async def process_promo_code_input(message: Message, state: FSMContext):
    """Обработка введённого кода."""
    code = message.text.strip().upper()
    
    # Валидация
    if not code.isalnum():
        await message.answer(
            "❌ Код может содержать только латинские буквы и цифры.\n"
            "Попробуйте ещё раз:"
        )
        return
    
    if len(code) < 4 or len(code) > 20:
        await message.answer(
            "❌ Длина кода должна быть от 4 до 20 символов.\n"
            "Попробуйте ещё раз:"
        )
        return
    
    # Проверка уникальности
    existing = await PromoCRUD.get_by_code(code)
    if existing:
        await message.answer(
            f"❌ Промокод <code>{code}</code> уже существует.\n"
            "Введите другой код:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(code=code)
    await state.set_state(PromoAdminState.selecting_discount_type)
    
    text = (
        f"✅ Код: <code>{code}</code>\n\n"
        "Выберите тип скидки:"
    )
    
    await message.answer(
        text,
        reply_markup=get_promo_discount_type_keyboard(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ — ШАГ 2B: АВТОГЕНЕРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:promo:create:auto")
async def promo_auto_generate(callback: CallbackQuery, state: FSMContext):
    """Автоматическая генерация одного кода."""
    code = generate_promo_code(8)
    
    # Проверяем уникальность
    while await PromoCRUD.get_by_code(code):
        code = generate_promo_code(8)
    
    await state.update_data(code=code, creation_type="auto")
    await state.set_state(PromoAdminState.selecting_discount_type)
    
    text = (
        f"🎲 <b>Сгенерирован код:</b> <code>{code}</code>\n\n"
        "Выберите тип скидки:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promo_discount_type_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ — ШАГ 2C: МАССОВАЯ ГЕНЕРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:promo:create:bulk")
async def promo_bulk_start(callback: CallbackQuery, state: FSMContext):
    """Начало массовой генерации."""
    await state.set_state(PromoAdminState.entering_bulk_count)
    await state.update_data(creation_type="bulk")
    
    text = (
        "📦 <b>Массовая генерация</b>\n\n"
        "Сколько промокодов создать?\n"
        "Введите число от 2 до 100:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard("admin:promos"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(StateFilter(PromoAdminState.entering_bulk_count))
async def process_bulk_count(message: Message, state: FSMContext):
    """Обработка количества для массовой генерации."""
    try:
        count = int(message.text.strip())
        if count < 2 or count > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 2 до 100:")
        return
    
    await state.update_data(bulk_count=count)
    await state.set_state(PromoAdminState.entering_bulk_prefix)
    
    text = (
        f"✅ Количество: <b>{count}</b>\n\n"
        "Введите префикс для кодов (необязательно).\n"
        "Например: <code>VIP</code> → <code>VIP8A3KM2</code>\n\n"
        "Отправьте <code>-</code> чтобы пропустить."
    )
    
    await message.answer(text, parse_mode="HTML")


@router.message(StateFilter(PromoAdminState.entering_bulk_prefix))
async def process_bulk_prefix(message: Message, state: FSMContext):
    """Обработка префикса для массовой генерации."""
    prefix = message.text.strip().upper()
    
    if prefix == "-":
        prefix = ""
    elif not prefix.isalnum():
        await message.answer("❌ Префикс может содержать только буквы и цифры:")
        return
    elif len(prefix) > 6:
        await message.answer("❌ Префикс слишком длинный (максимум 6 символов):")
        return
    
    await state.update_data(bulk_prefix=prefix)
    await state.set_state(PromoAdminState.selecting_discount_type)
    
    data = await state.get_data()
    count = data['bulk_count']
    
    # Генерируем превью кодов
    preview_codes = generate_promo_codes(min(3, count), 8, prefix)
    preview = ", ".join([f"<code>{c}</code>" for c in preview_codes])
    
    text = (
        f"✅ Будет создано: <b>{count} промокодов</b>\n"
        f"📝 Префикс: <b>{prefix if prefix else '—'}</b>\n"
        f"🔍 Пример: {preview}...\n\n"
        "Выберите тип скидки:"
    )
    
    await message.answer(
        text,
        reply_markup=get_promo_discount_type_keyboard(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ — ШАГ 3: ТИП СКИДКИ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(
    StateFilter(PromoAdminState.selecting_discount_type),
    F.data.startswith("admin:promo:discount:")
)
async def select_discount_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа скидки."""
    discount_type = callback.data.split(":")[3]
    await state.update_data(discount_type=discount_type)
    
    if discount_type == "percent":
        await state.set_state(PromoAdminState.entering_discount_percent)
        text = (
            "💵 <b>Скидка в процентах</b>\n\n"
            "Введите процент скидки (1-100):"
        )
    elif discount_type == "amount":
        await state.set_state(PromoAdminState.entering_discount_amount)
        text = (
            "💰 <b>Фиксированная скидка</b>\n\n"
            "Введите сумму скидки в USD:"
        )
    else:  # bonus_days
        await state.set_state(PromoAdminState.entering_bonus_days)
        text = (
            "📅 <b>Бонусные дни</b>\n\n"
            "Сколько дней добавить к подписке?"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard("admin:promos"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(StateFilter(PromoAdminState.entering_discount_percent))
async def process_discount_percent(message: Message, state: FSMContext):
    """Обработка процента скидки."""
    try:
        percent = int(message.text.strip())
        if percent < 1 or percent > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 1 до 100:")
        return
    
    await state.update_data(discount_percent=percent)
    await proceed_to_target_selection(message, state)


@router.message(StateFilter(PromoAdminState.entering_discount_amount))
async def process_discount_amount(message: Message, state: FSMContext):
    """Обработка суммы скидки."""
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0 or amount > 1000:
            raise ValueError
    except (ValueError, Exception):
        await message.answer("❌ Введите сумму от 0.01 до 1000 USD:")
        return
    
    await state.update_data(discount_amount=float(amount))
    await proceed_to_target_selection(message, state)


@router.message(StateFilter(PromoAdminState.entering_bonus_days))
async def process_bonus_days(message: Message, state: FSMContext):
    """Обработка бонусных дней."""
    try:
        days = int(message.text.strip())
        if days < 1 or days > 365:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите количество дней от 1 до 365:")
        return
    
    await state.update_data(bonus_days=days)
    await proceed_to_target_selection(message, state)


async def proceed_to_target_selection(message: Message, state: FSMContext):
    """Переход к выбору цели промокода."""
    await state.set_state(PromoAdminState.selecting_target)
    
    text = (
        "🎯 <b>На что распространяется промокод?</b>\n\n"
        "• <b>Все</b> — любой канал или пакет\n"
        "• <b>Канал</b> — конкретный канал\n"
        "• <b>Пакет</b> — конкретный пакет каналов"
    )
    
    await message.answer(
        text,
        reply_markup=get_promo_target_keyboard(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ — ШАГ 4: ЦЕЛЬ ПРОМОКОДА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(
    StateFilter(PromoAdminState.selecting_target),
    F.data.startswith("admin:promo:target:")
)
async def select_promo_target(callback: CallbackQuery, state: FSMContext):
    """Выбор цели применения промокода."""
    target = callback.data.split(":")[3]
    
    if target == "all":
        await state.update_data(channel_id=None, package_id=None)
        await proceed_to_limits(callback, state)
    
    elif target == "channel":
        # Получаем список каналов
        channels = await ChannelCRUD.get_all_active()
        if not channels:
            await callback.answer("❌ Нет активных каналов", show_alert=True)
            return
        
        await state.set_state(PromoAdminState.selecting_channel)
        
        text = "📢 <b>Выберите канал:</b>"
        await callback.message.edit_text(
            text,
            reply_markup=get_promo_channels_keyboard(channels),
            parse_mode="HTML"
        )
    
    else:  # package
        # Получаем список пакетов
        packages = await PackageCRUD.get_all_active()
        if not packages:
            await callback.answer("❌ Нет активных пакетов", show_alert=True)
            return
        
        await state.set_state(PromoAdminState.selecting_package)
        
        text = "📦 <b>Выберите пакет:</b>"
        await callback.message.edit_text(
            text,
            reply_markup=get_promo_packages_keyboard(packages),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(
    StateFilter(PromoAdminState.selecting_channel),
    F.data.startswith("admin:promo:channel:")
)
async def select_channel_for_promo(callback: CallbackQuery, state: FSMContext):
    """Выбор канала для промокода."""
    channel_id = int(callback.data.split(":")[3])
    await state.update_data(channel_id=channel_id, package_id=None)
    await proceed_to_limits(callback, state)
    await callback.answer()


@router.callback_query(
    StateFilter(PromoAdminState.selecting_package),
    F.data.startswith("admin:promo:package:")
)
async def select_package_for_promo(callback: CallbackQuery, state: FSMContext):
    """Выбор пакета для промокода."""
    package_id = int(callback.data.split(":")[3])
    await state.update_data(package_id=package_id, channel_id=None)
    await proceed_to_limits(callback, state)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ — ШАГ 5: ЛИМИТЫ
# ═══════════════════════════════════════════════════════════════════════════════

async def proceed_to_limits(callback: CallbackQuery, state: FSMContext):
    """Переход к настройке лимитов."""
    await state.set_state(PromoAdminState.entering_max_uses)
    
    text = (
        "🔢 <b>Лимит использований</b>\n\n"
        "Сколько раз можно использовать промокод?\n\n"
        "Введите число или <code>0</code> для безлимита:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard("admin:promos"),
        parse_mode="HTML"
    )


@router.message(StateFilter(PromoAdminState.entering_max_uses))
async def process_max_uses(message: Message, state: FSMContext):
    """Обработка лимита использований."""
    try:
        max_uses = int(message.text.strip())
        if max_uses < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число или 0:")
        return
    
    await state.update_data(max_uses=max_uses if max_uses > 0 else None)
    await state.set_state(PromoAdminState.entering_expires_days)
    
    text = (
        "📅 <b>Срок действия</b>\n\n"
        "Через сколько дней истечёт промокод?\n\n"
        "Введите число дней или <code>0</code> для бессрочного:"
    )
    
    await message.answer(text, parse_mode="HTML")


@router.message(StateFilter(PromoAdminState.entering_expires_days))
async def process_expires_days(message: Message, state: FSMContext):
    """Обработка срока действия."""
    try:
        days = int(message.text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число или 0:")
        return
    
    expires_at = None
    if days > 0:
        expires_at = datetime.utcnow() + timedelta(days=days)
    
    await state.update_data(expires_at=expires_at, expires_days=days)
    
    # Показываем подтверждение
    await show_promo_confirmation(message, state)


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ СОЗДАНИЕ — ШАГ 6: ПОДТВЕРЖДЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

async def show_promo_confirmation(message: Message, state: FSMContext):
    """Показ подтверждения перед созданием."""
    await state.set_state(PromoAdminState.confirming)
    data = await state.get_data()
    
    # Формируем текст подтверждения
    creation_type = data.get('creation_type', 'manual')
    
    if creation_type == "bulk":
        count = data.get('bulk_count', 0)
        prefix = data.get('bulk_prefix', '')
        code_info = f"📦 <b>Кодов:</b> {count}\n📝 <b>Префикс:</b> {prefix if prefix else '—'}"
    else:
        code_info = f"🎟️ <b>Код:</b> <code>{data.get('code', '—')}</code>"
    
    # Скидка
    if data.get('discount_percent'):
        discount = f"{data['discount_percent']}%"
    elif data.get('discount_amount'):
        discount = f"${data['discount_amount']}"
    elif data.get('bonus_days'):
        discount = f"+{data['bonus_days']} дней"
    else:
        discount = "—"
    
    # Цель
    if data.get('channel_id'):
        channel = await ChannelCRUD.get_by_id(data['channel_id'])
        target = f"📢 Канал: {channel.title if channel else '—'}"
    elif data.get('package_id'):
        package = await PackageCRUD.get_by_id(data['package_id'])
        target = f"📦 Пакет: {package.name if package else '—'}"
    else:
        target = "🌐 Все"
    
    # Лимиты
    max_uses = data.get('max_uses')
    uses_text = str(max_uses) if max_uses else "∞"
    
    expires_days = data.get('expires_days', 0)
    expires_text = f"{expires_days} дней" if expires_days > 0 else "Бессрочно"
    
    text = (
        "✅ <b>Проверьте данные промокода:</b>\n\n"
        f"{code_info}\n"
        f"💰 <b>Скидка:</b> {discount}\n"
        f"🎯 <b>Цель:</b> {target}\n"
        f"🔢 <b>Лимит:</b> {uses_text}\n"
        f"📅 <b>Срок:</b> {expires_text}\n\n"
        "Создать промокод?"
    )
    
    await message.answer(
        text,
        reply_markup=get_confirm_keyboard("admin:promo:confirm", "admin:promos"),
        parse_mode="HTML"
    )


@router.callback_query(
    StateFilter(PromoAdminState.confirming),
    F.data == "admin:promo:confirm"
)
async def confirm_promo_creation(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и создание промокода."""
    data = await state.get_data()
    creation_type = data.get('creation_type', 'manual')
    
    try:
        if creation_type == "bulk":
            # Массовое создание
            count = data.get('bulk_count', 0)
            prefix = data.get('bulk_prefix', '')
            codes = generate_promo_codes(count, 8, prefix)
            
            # Проверяем уникальность всех кодов
            unique_codes = []
            for code in codes:
                if not await PromoCRUD.get_by_code(code):
                    unique_codes.append(code)
            
            created_count = 0
            for code in unique_codes:
                await PromoCRUD.create(
                    code=code,
                    discount_percent=data.get('discount_percent'),
                    discount_amount=data.get('discount_amount'),
                    bonus_days=data.get('bonus_days'),
                    channel_id=data.get('channel_id'),
                    package_id=data.get('package_id'),
                    max_uses=data.get('max_uses'),
                    expires_at=data.get('expires_at'),
                    is_active=True
                )
                created_count += 1
            
            await state.clear()
            
            # Показываем результат
            codes_preview = "\n".join([f"<code>{c}</code>" for c in unique_codes[:10]])
            if len(unique_codes) > 10:
                codes_preview += f"\n... и ещё {len(unique_codes) - 10}"
            
            text = (
                f"✅ <b>Создано промокодов: {created_count}</b>\n\n"
                f"{codes_preview}"
            )
            
        else:
            # Одиночное создание
            code = data.get('code')
            
            promo = await PromoCRUD.create(
                code=code,
                discount_percent=data.get('discount_percent'),
                discount_amount=data.get('discount_amount'),
                bonus_days=data.get('bonus_days'),
                channel_id=data.get('channel_id'),
                package_id=data.get('package_id'),
                max_uses=data.get('max_uses'),
                expires_at=data.get('expires_at'),
                is_active=True
            )
            
            await state.clear()
            
            text = f"✅ <b>Промокод создан!</b>\n\n🎟️ <code>{code}</code>"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin:promos"),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error creating promo: {e}")
        await callback.answer("❌ Ошибка при создании промокода", show_alert=True)
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ✏️ РЕДАКТИРОВАНИЕ ПРОМОКОДА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:promo:edit:"))
async def show_promo_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования промокода."""
    promo_id = int(callback.data.split(":")[3])
    
    promo = await PromoCRUD.get_by_id(promo_id)
    if not promo:
        await callback.answer("❌ Промокод не найден", show_alert=True)
        return
    
    await state.update_data(editing_promo_id=promo_id)
    
    text = (
        f"✏️ <b>Редактирование промокода</b>\n\n"
        f"🎟️ <code>{promo.code}</code>\n\n"
        "Что изменить?"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promo_edit_keyboard(promo_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:promo:edit_code:"))
async def start_edit_promo_code(callback: CallbackQuery, state: FSMContext):
    """Начало изменения кода промокода."""
    promo_id = int(callback.data.split(":")[3])
    await state.update_data(editing_promo_id=promo_id)
    await state.set_state(PromoAdminState.editing_code)
    
    text = (
        "📝 <b>Введите новый код:</b>\n\n"
        "• Только латинские буквы и цифры\n"
        "• Длина: 4-20 символов"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(f"admin:promo:view:{promo_id}"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(StateFilter(PromoAdminState.editing_code))
async def process_edit_promo_code(message: Message, state: FSMContext):
    """Обработка нового кода промокода."""
    code = message.text.strip().upper()
    
    # Валидация
    if not code.isalnum() or len(code) < 4 or len(code) > 20:
        await message.answer("❌ Неверный формат кода. Попробуйте ещё раз:")
        return
    
    data = await state.get_data()
    promo_id = data.get('editing_promo_id')
    
    # Проверка уникальности
    existing = await PromoCRUD.get_by_code(code)
    if existing and existing.id != promo_id:
        await message.answer("❌ Этот код уже используется. Введите другой:")
        return
    
    # Обновляем
    await PromoCRUD.update(promo_id, code=code)
    await state.clear()
    
    await message.answer(
        f"✅ Код изменён на <code>{code}</code>",
        reply_markup=get_back_keyboard(f"admin:promo:view:{promo_id}"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:promo:edit_discount:"))
async def start_edit_discount(callback: CallbackQuery, state: FSMContext):
    """Начало изменения скидки."""
    promo_id = int(callback.data.split(":")[3])
    await state.update_data(editing_promo_id=promo_id)
    await state.set_state(PromoAdminState.editing_discount_type)
    
    text = "💰 <b>Выберите новый тип скидки:</b>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_promo_discount_type_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(
    StateFilter(PromoAdminState.editing_discount_type),
    F.data.startswith("admin:promo:discount:")
)
async def process_edit_discount_type(callback: CallbackQuery, state: FSMContext):
    """Выбор нового типа скидки при редактировании."""
    discount_type = callback.data.split(":")[3]
    await state.update_data(new_discount_type=discount_type)
    
    if discount_type == "percent":
        await state.set_state(PromoAdminState.editing_discount_value)
        text = "Введите новый процент скидки (1-100):"
    elif discount_type == "amount":
        await state.set_state(PromoAdminState.editing_discount_value)
        text = "Введите новую сумму скидки в USD:"
    else:
        await state.set_state(PromoAdminState.editing_discount_value)
        text = "Введите количество бонусных дней:"
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.message(StateFilter(PromoAdminState.editing_discount_value))
async def process_edit_discount_value(message: Message, state: FSMContext):
    """Обработка нового значения скидки."""
    data = await state.get_data()
    promo_id = data.get('editing_promo_id')
    discount_type = data.get('new_discount_type')
    
    try:
        value = message.text.strip()
        
        update_data = {
            'discount_percent': None,
            'discount_amount': None,
            'bonus_days': None
        }
        
        if discount_type == "percent":
            percent = int(value)
            if percent < 1 or percent > 100:
                raise ValueError
            update_data['discount_percent'] = percent
            result_text = f"{percent}%"
            
        elif discount_type == "amount":
            amount = float(value.replace(",", "."))
            if amount <= 0:
                raise ValueError
            update_data['discount_amount'] = amount
            result_text = f"${amount}"
            
        else:  # bonus_days
            days = int(value)
            if days < 1:
                raise ValueError
            update_data['bonus_days'] = days
            result_text = f"+{days} дней"
        
        await PromoCRUD.update(promo_id, **update_data)
        await state.clear()
        
        await message.answer(
            f"✅ Скидка изменена на <b>{result_text}</b>",
            reply_markup=get_back_keyboard(f"admin:promo:view:{promo_id}"),
            parse_mode="HTML"
        )
        
    except (ValueError, Exception):
        await message.answer("❌ Неверное значение. Попробуйте ещё раз:")


@router.callback_query(F.data.startswith("admin:promo:edit_limit:"))
async def start_edit_limit(callback: CallbackQuery, state: FSMContext):
    """Начало изменения лимита."""
    promo_id = int(callback.data.split(":")[3])
    await state.update_data(editing_promo_id=promo_id)
    await state.set_state(PromoAdminState.editing_limit)
    
    text = (
        "🔢 <b>Новый лимит использований</b>\n\n"
        "Введите число или <code>0</code> для безлимита:"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.message(StateFilter(PromoAdminState.editing_limit))
async def process_edit_limit(message: Message, state: FSMContext):
    """Обработка нового лимита."""
    try:
        limit = int(message.text.strip())
        if limit < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число или 0:")
        return
    
    data = await state.get_data()
    promo_id = data.get('editing_promo_id')
    
    await PromoCRUD.update(promo_id, max_uses=limit if limit > 0 else None)
    await state.clear()
    
    limit_text = str(limit) if limit > 0 else "∞"
    
    await message.answer(
        f"✅ Лимит изменён на <b>{limit_text}</b>",
        reply_markup=get_back_keyboard(f"admin:promo:view:{promo_id}"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:promo:edit_expires:"))
async def start_edit_expires(callback: CallbackQuery, state: FSMContext):
    """Начало изменения срока действия."""
    promo_id = int(callback.data.split(":")[3])
    await state.update_data(editing_promo_id=promo_id)
    await state.set_state(PromoAdminState.editing_expires)
    
    text = (
        "📅 <b>Новый срок действия</b>\n\n"
        "Через сколько дней истечёт промокод?\n"
        "Введите число или <code>0</code> для бессрочного:"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.message(StateFilter(PromoAdminState.editing_expires))
async def process_edit_expires(message: Message, state: FSMContext):
    """Обработка нового срока действия."""
    try:
        days = int(message.text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число или 0:")
        return
    
    data = await state.get_data()
    promo_id = data.get('editing_promo_id')
    
    expires_at = None
    if days > 0:
        expires_at = datetime.utcnow() + timedelta(days=days)
    
    await PromoCRUD.update(promo_id, expires_at=expires_at)
    await state.clear()
    
    expires_text = f"{days} дней" if days > 0 else "Бессрочно"
    
    await message.answer(
        f"✅ Срок действия: <b>{expires_text}</b>",
        reply_markup=get_back_keyboard(f"admin:promo:view:{promo_id}"),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 ПЕРЕКЛЮЧЕНИЕ АКТИВНОСТИ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:promo:toggle:"))
async def toggle_promo_active(callback: CallbackQuery):
    """Включение/выключение промокода."""
    promo_id = int(callback.data.split(":")[3])
    
    promo = await PromoCRUD.get_by_id(promo_id)
    if not promo:
        await callback.answer("❌ Промокод не найден", show_alert=True)
        return
    
    new_status = not promo.is_active
    await PromoCRUD.update(promo_id, is_active=new_status)
    
    status_text = "включён ✅" if new_status else "выключен ❌"
    await callback.answer(f"Промокод {status_text}", show_alert=True)
    
    # Обновляем детали
    await show_promo_details(callback, None)


# ═══════════════════════════════════════════════════════════════════════════════
# 🗑️ УДАЛЕНИЕ ПРОМОКОДА
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:promo:delete:"))
async def confirm_promo_delete(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления промокода."""
    promo_id = int(callback.data.split(":")[3])
    
    promo = await PromoCRUD.get_by_id(promo_id)
    if not promo:
        await callback.answer("❌ Промокод не найден", show_alert=True)
        return
    
    text = (
        f"🗑️ <b>Удаление промокода</b>\n\n"
        f"Вы уверены, что хотите удалить промокод\n"
        f"<code>{promo.code}</code>?\n\n"
        f"⚠️ Это действие необратимо!"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_keyboard(
            f"admin:promo:delete_confirm:{promo_id}",
            f"admin:promo:view:{promo_id}"
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:promo:delete_confirm:"))
async def delete_promo(callback: CallbackQuery, state: FSMContext):
    """Удаление промокода."""
    promo_id = int(callback.data.split(":")[3])
    
    await PromoCRUD.delete(promo_id)
    
    await callback.answer("✅ Промокод удалён", show_alert=True)
    
    # Возвращаемся к списку
    await show_promos_menu(callback, state)


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 СТАТИСТИКА ПРОМОКОДОВ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:promos:stats")
async def show_promos_stats(callback: CallbackQuery, state: FSMContext):
    """Детальная статистика по промокодам."""
    # Общая статистика
    total = await PromoCRUD.count_all()
    active = await PromoCRUD.count_active()
    expired = await PromoCRUD.count_expired()
    fully_used = await PromoCRUD.count_fully_used()
    
    # Статистика использования
    total_usage = await PromoUsageCRUD.count_all()
    usage_today = await PromoUsageCRUD.count_today()
    usage_week = await PromoUsageCRUD.count_this_week()
    usage_month = await PromoUsageCRUD.count_this_month()
    
    # Топ промокодов
    top_promos = await PromoCRUD.get_most_used(limit=5)
    
    text = (
        "📊 <b>Статистика промокодов</b>\n\n"
        
        "📋 <b>Промокоды:</b>\n"
        f"├ Всего: <b>{total}</b>\n"
        f"├ Активных: <b>{active}</b>\n"
        f"├ Истёкших: <b>{expired}</b>\n"
        f"└ Исчерпанных: <b>{fully_used}</b>\n\n"
        
        "📈 <b>Использование:</b>\n"
        f"├ Всего: <b>{total_usage}</b>\n"
        f"├ Сегодня: <b>{usage_today}</b>\n"
        f"├ За неделю: <b>{usage_week}</b>\n"
        f"└ За месяц: <b>{usage_month}</b>\n\n"
    )
    
    if top_promos:
        text += "🏆 <b>Топ-5 по использованию:</b>\n"
        for i, promo in enumerate(top_promos, 1):
            text += f"{i}. <code>{promo.code}</code> — {promo.used_count} раз\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("admin:promos"),
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 ФУНКЦИЯ ПОЛУЧЕНИЯ РОУТЕРА
# ═══════════════════════════════════════════════════════════════════════════════

def get_admin_promos_router() -> Router:
    """Возвращает роутер управления промокодами."""
    return router
