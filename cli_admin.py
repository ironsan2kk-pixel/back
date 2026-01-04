#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🖥️ CLI АДМИНКА — БЫСТРЫЕ КОМАНДЫ
═══════════════════════════════════════════════════════════════════════════════
Командная строка для быстрых операций без интерактивного TUI.

Использование:
    python cli_admin.py stats              # Показать статистику
    python cli_admin.py users --list       # Список пользователей
    python cli_admin.py users --search @username
    python cli_admin.py access --give 123456789 --channel 1 --days 30
    python cli_admin.py promo --create SALE50 --discount 50%
    python cli_admin.py promo --list
    python cli_admin.py channels --list
    python cli_admin.py broadcast --message "Привет!"
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Добавляем корневую папку проекта в путь
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

# Попытка импорта БД
try:
    from database.database import async_session_factory, init_db
    from database.crud import (
        ChannelCRUD, PackageCRUD, PricingCRUD, PromoCodeCRUD,
        UserCRUD, SubscriptionCRUD, PaymentCRUD, BroadcastCRUD,
        SettingsCRUD, StatisticsCRUD
    )
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 СТАТИСТИКА
# ═══════════════════════════════════════════════════════════════════════════════

async def show_stats():
    """Показать общую статистику."""
    console.print(Panel.fit("📊 СТАТИСТИКА", style="bold blue"))
    
    if not DATABASE_AVAILABLE:
        # Демо-данные
        stats = {
            "total_users": 1234,
            "active_subscriptions": 567,
            "monthly_revenue": 12345.00,
            "total_channels": 8,
            "total_packages": 5,
            "payments_today": 23,
            "new_users_week": 89,
            "active_promocodes": 12,
        }
    else:
        async with async_session_factory() as session:
            stats = await StatisticsCRUD.get_dashboard_stats(session)
    
    table = Table(box=box.ROUNDED)
    table.add_column("Показатель", style="cyan")
    table.add_column("Значение", style="green", justify="right")
    
    table.add_row("👥 Пользователей", f"{stats.get('total_users', 0):,}")
    table.add_row("✅ Активных подписок", f"{stats.get('active_subscriptions', 0):,}")
    table.add_row("💰 Доход за месяц", f"${stats.get('monthly_revenue', 0):,.2f}")
    table.add_row("📢 Каналов", f"{stats.get('total_channels', 0)}")
    table.add_row("📦 Пакетов", f"{stats.get('total_packages', 0)}")
    table.add_row("💳 Платежей сегодня", f"{stats.get('payments_today', 0)}")
    table.add_row("📈 Новых за неделю", f"{stats.get('new_users_week', 0)}")
    table.add_row("🎟️ Активных промокодов", f"{stats.get('active_promocodes', 0)}")
    
    console.print(table)


# ═══════════════════════════════════════════════════════════════════════════════
# 👥 ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════════════════════

async def list_users(limit: int = 20):
    """Список пользователей."""
    console.print(Panel.fit("👥 ПОЛЬЗОВАТЕЛИ", style="bold blue"))
    
    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Username", style="cyan")
    table.add_column("Имя")
    table.add_column("Язык")
    table.add_column("Подписок", justify="right")
    table.add_column("Потрачено", justify="right", style="green")
    table.add_column("Регистрация")
    
    if not DATABASE_AVAILABLE:
        # Демо-данные
        users = [
            ("123456789", "@john_doe", "John Doe", "🇺🇸", "2", "$59.98", "2024-12-01"),
            ("987654321", "@ivan_petrov", "Иван Петров", "🇷🇺", "3", "$149.97", "2024-11-15"),
            ("111222333", "@maria_s", "Maria S.", "🇺🇸", "1", "$29.99", "2025-01-02"),
        ]
        for user in users:
            table.add_row(*user)
    else:
        async with async_session_factory() as session:
            users = await UserCRUD.get_all(session, limit=limit)
            for user in users:
                lang = "🇷🇺" if user.language == "ru" else "🇺🇸"
                subs_count = len(user.subscriptions) if user.subscriptions else 0
                total_spent = sum(p.amount for p in user.payments if p.status == "completed") if user.payments else 0
                
                table.add_row(
                    str(user.user_id),
                    f"@{user.username}" if user.username else "N/A",
                    user.full_name or "N/A",
                    lang,
                    str(subs_count),
                    f"${total_spent:.2f}",
                    user.created_at.strftime("%Y-%m-%d")
                )
    
    console.print(table)


async def search_users(query: str):
    """Поиск пользователей."""
    console.print(Panel.fit(f"🔍 ПОИСК: {query}", style="bold blue"))
    
    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Username", style="cyan")
    table.add_column("Имя")
    table.add_column("Язык")
    
    if not DATABASE_AVAILABLE:
        console.print("[yellow]База данных недоступна. Демо-режим.[/yellow]")
        return
    
    async with async_session_factory() as session:
        users = await UserCRUD.search(session, query)
        for user in users:
            lang = "🇷🇺" if user.language == "ru" else "🇺🇸"
            table.add_row(
                str(user.user_id),
                f"@{user.username}" if user.username else "N/A",
                user.full_name or "N/A",
                lang
            )
    
    console.print(table)


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 КАНАЛЫ
# ═══════════════════════════════════════════════════════════════════════════════

async def list_channels():
    """Список каналов."""
    console.print(Panel.fit("📢 КАНАЛЫ", style="bold blue"))
    
    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Название", style="cyan")
    table.add_column("Username")
    table.add_column("ID канала")
    table.add_column("Статус")
    
    if not DATABASE_AVAILABLE:
        # Демо-данные
        channels = [
            ("1", "VIP Канал", "@vip_channel", "-1001234567890", "✅"),
            ("2", "Premium Content", "@premium_ch", "-1001234567891", "✅"),
            ("3", "Exclusive News", "@exclusive", "-1001234567892", "⏸️"),
        ]
        for ch in channels:
            table.add_row(*ch)
    else:
        async with async_session_factory() as session:
            channels = await ChannelCRUD.get_all(session)
            for ch in channels:
                status = "✅" if ch.is_active else "⏸️"
                table.add_row(
                    str(ch.id),
                    ch.name,
                    f"@{ch.username}" if ch.username else "N/A",
                    str(ch.channel_id),
                    status
                )
    
    console.print(table)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ПРОМОКОДЫ
# ═══════════════════════════════════════════════════════════════════════════════

async def list_promocodes():
    """Список промокодов."""
    console.print(Panel.fit("🎟️ ПРОМОКОДЫ", style="bold blue"))
    
    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Код", style="cyan")
    table.add_column("Тип")
    table.add_column("Скидка", justify="right")
    table.add_column("Использований", justify="right")
    table.add_column("Лимит", justify="right")
    table.add_column("Статус")
    
    if not DATABASE_AVAILABLE:
        # Демо-данные
        promos = [
            ("1", "WELCOME50", "Процент", "50%", "23", "100", "✅"),
            ("2", "NEWYEAR", "Фикс.", "$10", "45", "50", "✅"),
            ("3", "VIPFREE", "Бесплатно", "100%", "5", "10", "✅"),
        ]
        for p in promos:
            table.add_row(*p)
    else:
        async with async_session_factory() as session:
            promocodes = await PromoCodeCRUD.get_all(session)
            for promo in promocodes:
                if promo.discount_type == "percent":
                    discount = f"{promo.discount_value}%"
                    type_name = "Процент"
                elif promo.discount_type == "fixed":
                    discount = f"${promo.discount_value:.2f}"
                    type_name = "Фикс."
                else:
                    discount = "100%"
                    type_name = "Бесплатно"
                
                status = "✅" if promo.is_active else "⏸️"
                
                table.add_row(
                    str(promo.id),
                    promo.code,
                    type_name,
                    discount,
                    str(promo.uses_count),
                    str(promo.max_uses or "∞"),
                    status
                )
    
    console.print(table)


async def create_promocode(code: str, discount_type: str, value: float, max_uses: int = None):
    """Создать промокод."""
    if not DATABASE_AVAILABLE:
        console.print("[red]База данных недоступна![/red]")
        return
    
    async with async_session_factory() as session:
        promo = await PromoCodeCRUD.create(
            session,
            code=code.upper(),
            discount_type=discount_type,
            discount_value=value,
            max_uses=max_uses
        )
        console.print(f"[green]✅ Промокод '{code.upper()}' создан![/green]")


# ═══════════════════════════════════════════════════════════════════════════════
# 🎁 ВЫДАЧА ДОСТУПА
# ═══════════════════════════════════════════════════════════════════════════════

async def give_access(user_id: int, channel_id: int = None, package_id: int = None, days: int = 30):
    """Выдать доступ пользователю."""
    if not DATABASE_AVAILABLE:
        console.print("[red]База данных недоступна![/red]")
        return
    
    async with async_session_factory() as session:
        end_date = datetime.now() + timedelta(days=days)
        
        await SubscriptionCRUD.create(
            session,
            user_id=user_id,
            channel_id=channel_id,
            package_id=package_id,
            start_date=datetime.now(),
            end_date=end_date,
            is_active=True
        )
        
        if channel_id:
            console.print(f"[green]✅ Доступ к каналу {channel_id} выдан пользователю {user_id} на {days} дней![/green]")
        else:
            console.print(f"[green]✅ Доступ к пакету {package_id} выдан пользователю {user_id} на {days} дней![/green]")


# ═══════════════════════════════════════════════════════════════════════════════
# 📨 РАССЫЛКА
# ═══════════════════════════════════════════════════════════════════════════════

async def send_broadcast(message: str, target: str = "all"):
    """Отправить рассылку."""
    console.print(Panel.fit("📨 РАССЫЛКА", style="bold blue"))
    
    if not DATABASE_AVAILABLE:
        console.print("[yellow]База данных недоступна. Демо-режим.[/yellow]")
        console.print(f"[cyan]Сообщение:[/cyan] {message}")
        console.print(f"[cyan]Получатели:[/cyan] {target}")
        return
    
    # Здесь будет логика рассылки через aiogram
    console.print(f"[cyan]Сообщение:[/cyan] {message}")
    console.print(f"[cyan]Получатели:[/cyan] {target}")
    console.print("[yellow]⚠️ Для рассылки запустите основного бота![/yellow]")


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Главная функция CLI."""
    parser = argparse.ArgumentParser(
        description="CLI Админка для бота продажи доступов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python cli_admin.py stats              # Статистика
  python cli_admin.py users --list       # Список пользователей
  python cli_admin.py users --search @username
  python cli_admin.py channels --list    # Список каналов
  python cli_admin.py promo --list       # Список промокодов
  python cli_admin.py promo --create SALE50 --type percent --value 50
  python cli_admin.py access --give 123456789 --channel 1 --days 30
  python cli_admin.py broadcast --message "Привет всем!"
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Команда")
    
    # stats
    stats_parser = subparsers.add_parser("stats", help="Показать статистику")
    
    # users
    users_parser = subparsers.add_parser("users", help="Управление пользователями")
    users_parser.add_argument("--list", action="store_true", help="Список пользователей")
    users_parser.add_argument("--search", type=str, help="Поиск пользователя")
    users_parser.add_argument("--limit", type=int, default=20, help="Лимит записей")
    
    # channels
    channels_parser = subparsers.add_parser("channels", help="Управление каналами")
    channels_parser.add_argument("--list", action="store_true", help="Список каналов")
    
    # promo
    promo_parser = subparsers.add_parser("promo", help="Управление промокодами")
    promo_parser.add_argument("--list", action="store_true", help="Список промокодов")
    promo_parser.add_argument("--create", type=str, help="Создать промокод")
    promo_parser.add_argument("--type", type=str, choices=["percent", "fixed", "free"], default="percent")
    promo_parser.add_argument("--value", type=float, default=0, help="Значение скидки")
    promo_parser.add_argument("--uses", type=int, default=None, help="Лимит использований")
    
    # access
    access_parser = subparsers.add_parser("access", help="Выдача доступа")
    access_parser.add_argument("--give", type=int, help="User ID для выдачи доступа")
    access_parser.add_argument("--channel", type=int, help="ID канала")
    access_parser.add_argument("--package", type=int, help="ID пакета")
    access_parser.add_argument("--days", type=int, default=30, help="Количество дней")
    
    # broadcast
    broadcast_parser = subparsers.add_parser("broadcast", help="Рассылка")
    broadcast_parser.add_argument("--message", type=str, required=True, help="Текст сообщения")
    broadcast_parser.add_argument("--target", type=str, default="all", help="Получатели")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Выполняем команду
    if args.command == "stats":
        asyncio.run(show_stats())
    
    elif args.command == "users":
        if args.search:
            asyncio.run(search_users(args.search))
        else:
            asyncio.run(list_users(args.limit))
    
    elif args.command == "channels":
        asyncio.run(list_channels())
    
    elif args.command == "promo":
        if args.create:
            asyncio.run(create_promocode(args.create, args.type, args.value, args.uses))
        else:
            asyncio.run(list_promocodes())
    
    elif args.command == "access":
        if args.give:
            asyncio.run(give_access(args.give, args.channel, args.package, args.days))
        else:
            console.print("[red]Укажите --give USER_ID[/red]")
    
    elif args.command == "broadcast":
        asyncio.run(send_broadcast(args.message, args.target))


if __name__ == "__main__":
    main()
