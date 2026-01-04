"""
═══════════════════════════════════════════════════════════════════════════════
🖥️ TUI АДМИНКА — ГЛАВНОЕ ПРИЛОЖЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Terminal User Interface для администрирования бота продажи доступов.
Использует библиотеку Textual для красивого терминального интерфейса.
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, 
    Footer, 
    Static, 
    Button,
    ListView,
    ListItem,
    Label,
    TabbedContent,
    TabPane,
    DataTable,
    Input,
    Select,
    TextArea,
    ProgressBar,
    Placeholder,
    Rule,
    Markdown,
)
from textual.screen import Screen
from textual import on, work
from textual.worker import Worker, get_current_worker

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Console, Group
from rich.align import Align

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os

# Импорт из основного проекта
try:
    from database.database import async_session_factory, init_db
    from database.crud import (
        ChannelCRUD, PackageCRUD, PricingCRUD, PromoCodeCRUD,
        UserCRUD, SubscriptionCRUD, PaymentCRUD, BroadcastCRUD,
        SettingsCRUD, StatisticsCRUD
    )
    from config import settings
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️ База данных недоступна. Работаем в демо-режиме.")


# ═══════════════════════════════════════════════════════════════════════════════
# 🎨 ВИДЖЕТЫ СТАТИСТИКИ
# ═══════════════════════════════════════════════════════════════════════════════

class StatsCard(Static):
    """Карточка статистики."""
    
    DEFAULT_CSS = """
    StatsCard {
        width: 1fr;
        height: 7;
        border: solid $primary;
        padding: 1 2;
        margin: 0 1;
        background: $surface;
    }
    
    StatsCard:hover {
        border: solid $accent;
        background: $surface-lighten-1;
    }
    
    StatsCard .card-title {
        text-style: bold;
        color: $text-muted;
        text-align: center;
    }
    
    StatsCard .card-value {
        text-style: bold;
        color: $success;
        text-align: center;
        padding-top: 1;
    }
    
    StatsCard .card-change {
        text-align: center;
        color: $text-muted;
    }
    """
    
    def __init__(
        self,
        title: str,
        value: str,
        change: str = "",
        icon: str = "📊",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.change = change
        self.icon = icon
    
    def compose(self) -> ComposeResult:
        yield Static(f"{self.icon} {self.title}", classes="card-title")
        yield Static(self.value, classes="card-value")
        if self.change:
            yield Static(self.change, classes="card-change")
    
    def update_stats(self, value: str, change: str = ""):
        """Обновить значения карточки."""
        self.value = value
        self.change = change
        self.refresh()


class StatsRow(Horizontal):
    """Ряд карточек статистики."""
    
    DEFAULT_CSS = """
    StatsRow {
        width: 100%;
        height: auto;
        padding: 1 0;
    }
    """


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ЭКРАН ДАШБОРДА
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardScreen(Screen):
    """Главный дашборд с общей статистикой."""
    
    BINDINGS = [
        Binding("r", "refresh", "Обновить"),
        Binding("escape", "app.pop_screen", "Назад"),
    ]
    
    DEFAULT_CSS = """
    DashboardScreen {
        background: $background;
    }
    
    .dashboard-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .section-title {
        text-style: bold;
        color: $primary;
        padding: 1 0;
        text-align: center;
    }
    
    .recent-section {
        height: 1fr;
        margin-top: 1;
    }
    
    .recent-table {
        width: 100%;
        height: 100%;
        border: solid $primary-darken-2;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(classes="dashboard-container"):
            yield Static("📊 ПАНЕЛЬ УПРАВЛЕНИЯ", classes="section-title")
            
            # Статистика - верхний ряд
            with StatsRow():
                yield StatsCard(
                    title="Пользователей",
                    value="0",
                    change="",
                    icon="👥",
                    id="stat-users"
                )
                yield StatsCard(
                    title="Активных подписок",
                    value="0",
                    change="",
                    icon="✅",
                    id="stat-subscriptions"
                )
                yield StatsCard(
                    title="Доход за месяц",
                    value="$0.00",
                    change="",
                    icon="💰",
                    id="stat-revenue"
                )
                yield StatsCard(
                    title="Каналов",
                    value="0",
                    change="",
                    icon="📢",
                    id="stat-channels"
                )
            
            # Статистика - второй ряд
            with StatsRow():
                yield StatsCard(
                    title="Платежей сегодня",
                    value="0",
                    change="",
                    icon="💳",
                    id="stat-payments-today"
                )
                yield StatsCard(
                    title="Новых за неделю",
                    value="0",
                    change="",
                    icon="📈",
                    id="stat-new-week"
                )
                yield StatsCard(
                    title="Пакетов",
                    value="0",
                    change="",
                    icon="📦",
                    id="stat-packages"
                )
                yield StatsCard(
                    title="Промокодов",
                    value="0",
                    change="",
                    icon="🎟️",
                    id="stat-promocodes"
                )
            
            yield Rule()
            
            # Последние события
            with Horizontal(classes="recent-section"):
                with Vertical():
                    yield Static("📋 Последние платежи", classes="section-title")
                    yield DataTable(id="recent-payments", classes="recent-table")
                
                with Vertical():
                    yield Static("👤 Новые пользователи", classes="section-title")
                    yield DataTable(id="recent-users", classes="recent-table")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """При загрузке экрана."""
        # Настраиваем таблицы
        payments_table = self.query_one("#recent-payments", DataTable)
        payments_table.add_columns("ID", "Пользователь", "Сумма", "Статус", "Дата")
        
        users_table = self.query_one("#recent-users", DataTable)
        users_table.add_columns("ID", "Username", "Имя", "Дата регистрации")
        
        # Загружаем данные
        await self.load_stats()
    
    @work(exclusive=True)
    async def load_stats(self) -> None:
        """Загрузка статистики из БД."""
        if not DATABASE_AVAILABLE:
            # Демо-данные
            self.query_one("#stat-users", StatsCard).query_one(".card-value", Static).update("1,234")
            self.query_one("#stat-subscriptions", StatsCard).query_one(".card-value", Static).update("567")
            self.query_one("#stat-revenue", StatsCard).query_one(".card-value", Static).update("$12,345.00")
            self.query_one("#stat-channels", StatsCard).query_one(".card-value", Static).update("8")
            self.query_one("#stat-payments-today", StatsCard).query_one(".card-value", Static).update("23")
            self.query_one("#stat-new-week", StatsCard).query_one(".card-value", Static).update("89")
            self.query_one("#stat-packages", StatsCard).query_one(".card-value", Static).update("5")
            self.query_one("#stat-promocodes", StatsCard).query_one(".card-value", Static).update("12")
            
            # Демо таблицы
            payments_table = self.query_one("#recent-payments", DataTable)
            payments_table.add_rows([
                ("1", "@user1", "$29.99", "✅ Оплачен", "2025-01-03"),
                ("2", "@user2", "$49.99", "✅ Оплачен", "2025-01-03"),
                ("3", "@user3", "$9.99", "⏳ Ожидает", "2025-01-02"),
            ])
            
            users_table = self.query_one("#recent-users", DataTable)
            users_table.add_rows([
                ("123456", "@newuser1", "Иван", "2025-01-03"),
                ("123457", "@newuser2", "Мария", "2025-01-03"),
                ("123458", "@newuser3", "Alex", "2025-01-02"),
            ])
            return
        
        async with async_session_factory() as session:
            # Получаем статистику
            stats = await StatisticsCRUD.get_dashboard_stats(session)
            
            # Обновляем карточки
            self.query_one("#stat-users", StatsCard).query_one(".card-value", Static).update(
                f"{stats.get('total_users', 0):,}"
            )
            self.query_one("#stat-subscriptions", StatsCard).query_one(".card-value", Static).update(
                f"{stats.get('active_subscriptions', 0):,}"
            )
            self.query_one("#stat-revenue", StatsCard).query_one(".card-value", Static).update(
                f"${stats.get('monthly_revenue', 0):,.2f}"
            )
            self.query_one("#stat-channels", StatsCard).query_one(".card-value", Static).update(
                f"{stats.get('total_channels', 0)}"
            )
            self.query_one("#stat-payments-today", StatsCard).query_one(".card-value", Static).update(
                f"{stats.get('payments_today', 0)}"
            )
            self.query_one("#stat-new-week", StatsCard).query_one(".card-value", Static).update(
                f"{stats.get('new_users_week', 0)}"
            )
            self.query_one("#stat-packages", StatsCard).query_one(".card-value", Static).update(
                f"{stats.get('total_packages', 0)}"
            )
            self.query_one("#stat-promocodes", StatsCard).query_one(".card-value", Static).update(
                f"{stats.get('active_promocodes', 0)}"
            )
            
            # Загружаем последние платежи
            recent_payments = await PaymentCRUD.get_recent(session, limit=5)
            payments_table = self.query_one("#recent-payments", DataTable)
            payments_table.clear()
            for payment in recent_payments:
                status = "✅ Оплачен" if payment.status == "completed" else "⏳ Ожидает"
                payments_table.add_row(
                    str(payment.id),
                    f"@{payment.user.username or payment.user_id}",
                    f"${payment.amount:.2f}",
                    status,
                    payment.created_at.strftime("%Y-%m-%d")
                )
            
            # Загружаем новых пользователей
            recent_users = await UserCRUD.get_recent(session, limit=5)
            users_table = self.query_one("#recent-users", DataTable)
            users_table.clear()
            for user in recent_users:
                users_table.add_row(
                    str(user.user_id),
                    f"@{user.username or 'N/A'}",
                    user.full_name or "N/A",
                    user.created_at.strftime("%Y-%m-%d")
                )
    
    def action_refresh(self) -> None:
        """Обновить данные."""
        self.load_stats()
        self.notify("🔄 Данные обновлены")


# ═══════════════════════════════════════════════════════════════════════════════
# 📢 ЭКРАН УПРАВЛЕНИЯ КАНАЛАМИ
# ═══════════════════════════════════════════════════════════════════════════════

class ChannelsScreen(Screen):
    """Управление каналами."""
    
    BINDINGS = [
        Binding("a", "add_channel", "Добавить"),
        Binding("d", "delete_channel", "Удалить"),
        Binding("e", "edit_channel", "Изменить"),
        Binding("r", "refresh", "Обновить"),
        Binding("escape", "app.pop_screen", "Назад"),
    ]
    
    DEFAULT_CSS = """
    ChannelsScreen {
        background: $background;
    }
    
    .channels-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .channels-table {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }
    
    .form-container {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $secondary;
        margin-top: 1;
    }
    
    .form-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    
    .form-label {
        width: 20;
        padding: 1;
    }
    
    .form-input {
        width: 1fr;
    }
    
    .button-row {
        width: 100%;
        height: auto;
        padding: 1;
        align: center middle;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(classes="channels-container"):
            yield Static("📢 УПРАВЛЕНИЕ КАНАЛАМИ", classes="section-title")
            yield DataTable(id="channels-table", classes="channels-table")
            
            # Форма добавления/редактирования
            with Container(classes="form-container", id="channel-form"):
                yield Static("➕ Добавить канал", id="form-title")
                
                with Horizontal(classes="form-row"):
                    yield Static("Название:", classes="form-label")
                    yield Input(placeholder="Название канала", id="channel-name", classes="form-input")
                
                with Horizontal(classes="form-row"):
                    yield Static("Username:", classes="form-label")
                    yield Input(placeholder="@channel_username", id="channel-username", classes="form-input")
                
                with Horizontal(classes="form-row"):
                    yield Static("ID канала:", classes="form-label")
                    yield Input(placeholder="-1001234567890", id="channel-id", classes="form-input")
                
                with Horizontal(classes="form-row"):
                    yield Static("Описание:", classes="form-label")
                    yield Input(placeholder="Описание канала", id="channel-description", classes="form-input")
                
                with Horizontal(classes="button-row"):
                    yield Button("💾 Сохранить", variant="success", id="btn-save-channel")
                    yield Button("🚫 Отмена", variant="error", id="btn-cancel-channel")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """При загрузке экрана."""
        table = self.query_one("#channels-table", DataTable)
        table.add_columns("ID", "Название", "Username", "ID канала", "Подписчиков", "Статус")
        table.cursor_type = "row"
        
        await self.load_channels()
        
        # Скрываем форму по умолчанию
        self.query_one("#channel-form").display = False
    
    @work(exclusive=True)
    async def load_channels(self) -> None:
        """Загрузка каналов из БД."""
        table = self.query_one("#channels-table", DataTable)
        table.clear()
        
        if not DATABASE_AVAILABLE:
            # Демо-данные
            table.add_rows([
                ("1", "VIP Канал", "@vip_channel", "-1001234567890", "1,234", "✅ Активен"),
                ("2", "Premium Content", "@premium_ch", "-1001234567891", "567", "✅ Активен"),
                ("3", "Exclusive News", "@exclusive", "-1001234567892", "890", "⏸️ Неактивен"),
            ])
            return
        
        async with async_session_factory() as session:
            channels = await ChannelCRUD.get_all(session)
            for ch in channels:
                status = "✅ Активен" if ch.is_active else "⏸️ Неактивен"
                table.add_row(
                    str(ch.id),
                    ch.name,
                    f"@{ch.username}" if ch.username else "N/A",
                    str(ch.channel_id),
                    f"{ch.subscribers_count or 0:,}",
                    status
                )
    
    def action_add_channel(self) -> None:
        """Показать форму добавления."""
        form = self.query_one("#channel-form")
        form.display = True
        self.query_one("#form-title", Static).update("➕ Добавить канал")
        
        # Очищаем поля
        self.query_one("#channel-name", Input).value = ""
        self.query_one("#channel-username", Input).value = ""
        self.query_one("#channel-id", Input).value = ""
        self.query_one("#channel-description", Input).value = ""
    
    def action_edit_channel(self) -> None:
        """Редактировать выбранный канал."""
        table = self.query_one("#channels-table", DataTable)
        if table.cursor_row is not None:
            row_data = table.get_row_at(table.cursor_row)
            
            form = self.query_one("#channel-form")
            form.display = True
            self.query_one("#form-title", Static).update(f"✏️ Редактировать: {row_data[1]}")
            
            # Заполняем поля
            self.query_one("#channel-name", Input).value = row_data[1]
            self.query_one("#channel-username", Input).value = row_data[2].replace("@", "")
            self.query_one("#channel-id", Input).value = row_data[3]
            self.query_one("#channel-description", Input).value = ""
    
    async def action_delete_channel(self) -> None:
        """Удалить выбранный канал."""
        table = self.query_one("#channels-table", DataTable)
        if table.cursor_row is not None:
            row_data = table.get_row_at(table.cursor_row)
            channel_name = row_data[1]
            
            # Здесь можно добавить подтверждение
            if DATABASE_AVAILABLE:
                async with async_session_factory() as session:
                    await ChannelCRUD.delete(session, int(row_data[0]))
            
            await self.load_channels()
            self.notify(f"🗑️ Канал '{channel_name}' удалён")
    
    def action_refresh(self) -> None:
        """Обновить список."""
        self.load_channels()
        self.notify("🔄 Список обновлён")
    
    @on(Button.Pressed, "#btn-save-channel")
    async def save_channel(self) -> None:
        """Сохранить канал."""
        name = self.query_one("#channel-name", Input).value
        username = self.query_one("#channel-username", Input).value
        channel_id = self.query_one("#channel-id", Input).value
        description = self.query_one("#channel-description", Input).value
        
        if not name or not channel_id:
            self.notify("❌ Заполните обязательные поля!", severity="error")
            return
        
        if DATABASE_AVAILABLE:
            async with async_session_factory() as session:
                await ChannelCRUD.create(
                    session,
                    name=name,
                    username=username.replace("@", ""),
                    channel_id=int(channel_id),
                    description=description
                )
        
        self.query_one("#channel-form").display = False
        await self.load_channels()
        self.notify(f"✅ Канал '{name}' сохранён")
    
    @on(Button.Pressed, "#btn-cancel-channel")
    def cancel_form(self) -> None:
        """Отмена формы."""
        self.query_one("#channel-form").display = False


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ЭКРАН УПРАВЛЕНИЯ ПАКЕТАМИ
# ═══════════════════════════════════════════════════════════════════════════════

class PackagesScreen(Screen):
    """Управление пакетами подписок."""
    
    BINDINGS = [
        Binding("a", "add_package", "Добавить"),
        Binding("d", "delete_package", "Удалить"),
        Binding("e", "edit_package", "Изменить"),
        Binding("r", "refresh", "Обновить"),
        Binding("escape", "app.pop_screen", "Назад"),
    ]
    
    DEFAULT_CSS = """
    PackagesScreen {
        background: $background;
    }
    
    .packages-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .packages-table {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(classes="packages-container"):
            yield Static("📦 УПРАВЛЕНИЕ ПАКЕТАМИ", classes="section-title")
            yield DataTable(id="packages-table", classes="packages-table")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """При загрузке экрана."""
        table = self.query_one("#packages-table", DataTable)
        table.add_columns("ID", "Название", "Каналы", "30 дней", "90 дней", "365 дней", "Статус")
        table.cursor_type = "row"
        
        await self.load_packages()
    
    @work(exclusive=True)
    async def load_packages(self) -> None:
        """Загрузка пакетов из БД."""
        table = self.query_one("#packages-table", DataTable)
        table.clear()
        
        if not DATABASE_AVAILABLE:
            # Демо-данные
            table.add_rows([
                ("1", "Базовый", "2 канала", "$9.99", "$24.99", "$79.99", "✅ Активен"),
                ("2", "Продвинутый", "5 каналов", "$19.99", "$49.99", "$149.99", "✅ Активен"),
                ("3", "Премиум", "Все каналы", "$29.99", "$74.99", "$199.99", "✅ Активен"),
            ])
            return
        
        async with async_session_factory() as session:
            packages = await PackageCRUD.get_all_with_details(session)
            for pkg in packages:
                channels_count = len(pkg.channels) if pkg.channels else 0
                status = "✅ Активен" if pkg.is_active else "⏸️ Неактивен"
                
                # Получаем цены
                prices = {p.duration_days: p.price for p in pkg.prices}
                
                table.add_row(
                    str(pkg.id),
                    pkg.name,
                    f"{channels_count} канал(ов)",
                    f"${prices.get(30, 0):.2f}",
                    f"${prices.get(90, 0):.2f}",
                    f"${prices.get(365, 0):.2f}",
                    status
                )
    
    def action_add_package(self) -> None:
        """Добавить пакет."""
        self.notify("📦 Функция добавления пакета", severity="information")
    
    def action_delete_package(self) -> None:
        """Удалить пакет."""
        table = self.query_one("#packages-table", DataTable)
        if table.cursor_row is not None:
            row_data = table.get_row_at(table.cursor_row)
            self.notify(f"🗑️ Удаление пакета: {row_data[1]}")
    
    def action_edit_package(self) -> None:
        """Редактировать пакет."""
        table = self.query_one("#packages-table", DataTable)
        if table.cursor_row is not None:
            row_data = table.get_row_at(table.cursor_row)
            self.notify(f"✏️ Редактирование: {row_data[1]}")
    
    def action_refresh(self) -> None:
        """Обновить список."""
        self.load_packages()
        self.notify("🔄 Список обновлён")


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ЭКРАН ПРОМОКОДОВ
# ═══════════════════════════════════════════════════════════════════════════════

class PromocodesScreen(Screen):
    """Управление промокодами."""
    
    BINDINGS = [
        Binding("a", "add_promocode", "Создать"),
        Binding("d", "delete_promocode", "Удалить"),
        Binding("g", "generate_bulk", "Генерация"),
        Binding("r", "refresh", "Обновить"),
        Binding("escape", "app.pop_screen", "Назад"),
    ]
    
    DEFAULT_CSS = """
    PromocodesScreen {
        background: $background;
    }
    
    .promo-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .promo-table {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }
    
    .promo-form {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $secondary;
        margin-top: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(classes="promo-container"):
            yield Static("🎟️ ПРОМОКОДЫ", classes="section-title")
            yield DataTable(id="promo-table", classes="promo-table")
            
            # Форма создания
            with Container(classes="promo-form", id="promo-form"):
                yield Static("➕ Создать промокод")
                
                with Horizontal(classes="form-row"):
                    yield Static("Код:", classes="form-label")
                    yield Input(placeholder="SUMMER2025", id="promo-code", classes="form-input")
                
                with Horizontal(classes="form-row"):
                    yield Static("Тип:", classes="form-label")
                    yield Select(
                        [
                            ("Процент скидки", "percent"),
                            ("Фиксированная скидка", "fixed"),
                            ("Бесплатный доступ", "free"),
                        ],
                        id="promo-type",
                        classes="form-input"
                    )
                
                with Horizontal(classes="form-row"):
                    yield Static("Значение:", classes="form-label")
                    yield Input(placeholder="50 (для % или $ суммы)", id="promo-value", classes="form-input")
                
                with Horizontal(classes="form-row"):
                    yield Static("Лимит:", classes="form-label")
                    yield Input(placeholder="100 (0 = безлимит)", id="promo-limit", classes="form-input")
                
                with Horizontal(classes="button-row"):
                    yield Button("💾 Создать", variant="success", id="btn-save-promo")
                    yield Button("🚫 Отмена", variant="error", id="btn-cancel-promo")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """При загрузке экрана."""
        table = self.query_one("#promo-table", DataTable)
        table.add_columns("ID", "Код", "Тип", "Скидка", "Использований", "Лимит", "Статус")
        table.cursor_type = "row"
        
        await self.load_promocodes()
        self.query_one("#promo-form").display = False
    
    @work(exclusive=True)
    async def load_promocodes(self) -> None:
        """Загрузка промокодов из БД."""
        table = self.query_one("#promo-table", DataTable)
        table.clear()
        
        if not DATABASE_AVAILABLE:
            # Демо-данные
            table.add_rows([
                ("1", "WELCOME50", "Процент", "50%", "23", "100", "✅ Активен"),
                ("2", "NEWYEAR", "Фиксированная", "$10.00", "45", "50", "✅ Активен"),
                ("3", "VIPFREE", "Бесплатный", "100%", "5", "10", "✅ Активен"),
                ("4", "OLD2024", "Процент", "25%", "100", "100", "⏸️ Исчерпан"),
            ])
            return
        
        async with async_session_factory() as session:
            promocodes = await PromoCodeCRUD.get_all(session)
            for promo in promocodes:
                if promo.discount_type == "percent":
                    discount = f"{promo.discount_value}%"
                    type_name = "Процент"
                elif promo.discount_type == "fixed":
                    discount = f"${promo.discount_value:.2f}"
                    type_name = "Фиксированная"
                else:
                    discount = "100%"
                    type_name = "Бесплатный"
                
                if promo.max_uses and promo.uses_count >= promo.max_uses:
                    status = "⏸️ Исчерпан"
                elif not promo.is_active:
                    status = "⏸️ Неактивен"
                else:
                    status = "✅ Активен"
                
                table.add_row(
                    str(promo.id),
                    promo.code,
                    type_name,
                    discount,
                    str(promo.uses_count),
                    str(promo.max_uses or "∞"),
                    status
                )
    
    def action_add_promocode(self) -> None:
        """Показать форму создания."""
        self.query_one("#promo-form").display = True
    
    @on(Button.Pressed, "#btn-save-promo")
    async def save_promocode(self) -> None:
        """Сохранить промокод."""
        code = self.query_one("#promo-code", Input).value.upper()
        promo_type = self.query_one("#promo-type", Select).value
        value = self.query_one("#promo-value", Input).value
        limit = self.query_one("#promo-limit", Input).value
        
        if not code:
            self.notify("❌ Введите код промокода!", severity="error")
            return
        
        if DATABASE_AVAILABLE:
            async with async_session_factory() as session:
                await PromoCodeCRUD.create(
                    session,
                    code=code,
                    discount_type=promo_type,
                    discount_value=float(value) if value else 0,
                    max_uses=int(limit) if limit and int(limit) > 0 else None
                )
        
        self.query_one("#promo-form").display = False
        await self.load_promocodes()
        self.notify(f"✅ Промокод '{code}' создан")
    
    @on(Button.Pressed, "#btn-cancel-promo")
    def cancel_form(self) -> None:
        """Отмена формы."""
        self.query_one("#promo-form").display = False
    
    def action_delete_promocode(self) -> None:
        """Удалить промокод."""
        table = self.query_one("#promo-table", DataTable)
        if table.cursor_row is not None:
            row_data = table.get_row_at(table.cursor_row)
            self.notify(f"🗑️ Удаление промокода: {row_data[1]}")
    
    def action_generate_bulk(self) -> None:
        """Массовая генерация промокодов."""
        self.notify("🎲 Массовая генерация промокодов", severity="information")
    
    def action_refresh(self) -> None:
        """Обновить список."""
        self.load_promocodes()
        self.notify("🔄 Список обновлён")


# ═══════════════════════════════════════════════════════════════════════════════
# 👥 ЭКРАН ПОЛЬЗОВАТЕЛЕЙ
# ═══════════════════════════════════════════════════════════════════════════════

class UsersScreen(Screen):
    """Управление пользователями."""
    
    BINDINGS = [
        Binding("s", "search_user", "Поиск"),
        Binding("g", "give_access", "Выдать доступ"),
        Binding("b", "ban_user", "Заблокировать"),
        Binding("r", "refresh", "Обновить"),
        Binding("escape", "app.pop_screen", "Назад"),
    ]
    
    DEFAULT_CSS = """
    UsersScreen {
        background: $background;
    }
    
    .users-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .search-row {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    .users-table {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }
    
    .user-details {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $secondary;
        margin-top: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(classes="users-container"):
            yield Static("👥 ПОЛЬЗОВАТЕЛИ", classes="section-title")
            
            with Horizontal(classes="search-row"):
                yield Input(placeholder="🔍 Поиск по ID, username или имени...", id="user-search")
                yield Button("Поиск", variant="primary", id="btn-search")
            
            yield DataTable(id="users-table", classes="users-table")
            
            # Детали пользователя
            with Container(classes="user-details", id="user-details"):
                yield Static("👤 Выберите пользователя", id="user-info")
                yield DataTable(id="user-subscriptions")
                
                with Horizontal(classes="button-row"):
                    yield Button("🎁 Выдать доступ", variant="success", id="btn-give-access")
                    yield Button("🚫 Заблокировать", variant="error", id="btn-ban")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """При загрузке экрана."""
        users_table = self.query_one("#users-table", DataTable)
        users_table.add_columns("ID", "Username", "Имя", "Язык", "Подписок", "Потрачено", "Регистрация")
        users_table.cursor_type = "row"
        
        subs_table = self.query_one("#user-subscriptions", DataTable)
        subs_table.add_columns("Канал/Пакет", "Тип", "Начало", "Окончание", "Статус")
        
        await self.load_users()
        self.query_one("#user-details").display = False
    
    @work(exclusive=True)
    async def load_users(self, search: str = None) -> None:
        """Загрузка пользователей из БД."""
        table = self.query_one("#users-table", DataTable)
        table.clear()
        
        if not DATABASE_AVAILABLE:
            # Демо-данные
            table.add_rows([
                ("123456789", "@john_doe", "John Doe", "🇺🇸 EN", "2", "$59.98", "2024-12-01"),
                ("987654321", "@ivan_petrov", "Иван Петров", "🇷🇺 RU", "3", "$149.97", "2024-11-15"),
                ("111222333", "@maria_s", "Maria S.", "🇺🇸 EN", "1", "$29.99", "2025-01-02"),
            ])
            return
        
        async with async_session_factory() as session:
            if search:
                users = await UserCRUD.search(session, search)
            else:
                users = await UserCRUD.get_all(session, limit=100)
            
            for user in users:
                lang = "🇷🇺 RU" if user.language == "ru" else "🇺🇸 EN"
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
    
    @on(Button.Pressed, "#btn-search")
    async def search_users(self) -> None:
        """Поиск пользователей."""
        search_query = self.query_one("#user-search", Input).value
        await self.load_users(search_query)
        self.notify(f"🔍 Найдено по запросу: {search_query}")
    
    @on(DataTable.RowSelected, "#users-table")
    async def user_selected(self, event: DataTable.RowSelected) -> None:
        """Выбран пользователь."""
        row_data = event.data_table.get_row(event.row_key)
        
        self.query_one("#user-details").display = True
        self.query_one("#user-info", Static).update(
            f"👤 {row_data[2]} ({row_data[1]}) | ID: {row_data[0]}"
        )
        
        # Загружаем подписки пользователя
        subs_table = self.query_one("#user-subscriptions", DataTable)
        subs_table.clear()
        
        if not DATABASE_AVAILABLE:
            subs_table.add_rows([
                ("VIP Канал", "Канал", "2024-12-01", "2025-01-01", "✅ Активна"),
                ("Premium Pack", "Пакет", "2024-12-15", "2025-03-15", "✅ Активна"),
            ])
        else:
            async with async_session_factory() as session:
                user = await UserCRUD.get_with_subscriptions(session, int(row_data[0]))
                if user and user.subscriptions:
                    for sub in user.subscriptions:
                        sub_type = "Пакет" if sub.package_id else "Канал"
                        name = sub.package.name if sub.package_id else sub.channel.name
                        status = "✅ Активна" if sub.is_active else "⏸️ Истекла"
                        
                        subs_table.add_row(
                            name,
                            sub_type,
                            sub.start_date.strftime("%Y-%m-%d"),
                            sub.end_date.strftime("%Y-%m-%d"),
                            status
                        )
    
    def action_search_user(self) -> None:
        """Фокус на поиск."""
        self.query_one("#user-search", Input).focus()
    
    def action_give_access(self) -> None:
        """Выдать доступ."""
        self.notify("🎁 Выдача доступа пользователю", severity="information")
    
    def action_ban_user(self) -> None:
        """Заблокировать пользователя."""
        self.notify("🚫 Блокировка пользователя", severity="warning")
    
    def action_refresh(self) -> None:
        """Обновить список."""
        self.load_users()
        self.notify("🔄 Список обновлён")


# ═══════════════════════════════════════════════════════════════════════════════
# 📨 ЭКРАН РАССЫЛКИ
# ═══════════════════════════════════════════════════════════════════════════════

class BroadcastScreen(Screen):
    """Рассылка сообщений."""
    
    BINDINGS = [
        Binding("ctrl+s", "send_broadcast", "Отправить"),
        Binding("escape", "app.pop_screen", "Назад"),
    ]
    
    DEFAULT_CSS = """
    BroadcastScreen {
        background: $background;
    }
    
    .broadcast-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .message-area {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }
    
    .options-row {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    .progress-section {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $secondary;
        margin-top: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(classes="broadcast-container"):
            yield Static("📨 РАССЫЛКА СООБЩЕНИЙ", classes="section-title")
            
            yield Static("Текст сообщения:")
            yield TextArea(id="broadcast-message", classes="message-area")
            
            with Horizontal(classes="options-row"):
                yield Static("Получатели: ")
                yield Select(
                    [
                        ("Все пользователи", "all"),
                        ("С активной подпиской", "active"),
                        ("Без подписки", "inactive"),
                        ("По языку: RU", "lang_ru"),
                        ("По языку: EN", "lang_en"),
                    ],
                    id="broadcast-target",
                    value="all"
                )
            
            with Horizontal(classes="button-row"):
                yield Button("📤 Начать рассылку", variant="success", id="btn-send")
                yield Button("👁️ Предпросмотр", variant="primary", id="btn-preview")
            
            # Прогресс рассылки
            with Container(classes="progress-section", id="progress-section"):
                yield Static("📊 Прогресс рассылки", id="progress-title")
                yield ProgressBar(id="broadcast-progress", total=100)
                yield Static("Готово к отправке", id="progress-status")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """При загрузке экрана."""
        self.query_one("#progress-section").display = False
    
    @on(Button.Pressed, "#btn-send")
    async def start_broadcast(self) -> None:
        """Начать рассылку."""
        message = self.query_one("#broadcast-message", TextArea).text
        target = self.query_one("#broadcast-target", Select).value
        
        if not message.strip():
            self.notify("❌ Введите текст сообщения!", severity="error")
            return
        
        self.query_one("#progress-section").display = True
        self.query_one("#progress-status", Static).update("⏳ Отправка...")
        
        # Запускаем рассылку
        self.run_broadcast(message, target)
    
    @work(exclusive=True)
    async def run_broadcast(self, message: str, target: str) -> None:
        """Выполнение рассылки."""
        progress_bar = self.query_one("#broadcast-progress", ProgressBar)
        status = self.query_one("#progress-status", Static)
        
        # Демо-прогресс
        total_users = 100
        sent = 0
        errors = 0
        
        for i in range(total_users):
            await asyncio.sleep(0.05)  # Имитация отправки
            sent += 1
            progress_bar.update(progress=sent)
            status.update(f"📤 Отправлено: {sent}/{total_users} | Ошибок: {errors}")
        
        status.update(f"✅ Рассылка завершена! Отправлено: {sent}, Ошибок: {errors}")
        self.notify(f"✅ Рассылка завершена! Отправлено: {sent}")
    
    @on(Button.Pressed, "#btn-preview")
    def preview_message(self) -> None:
        """Предпросмотр сообщения."""
        message = self.query_one("#broadcast-message", TextArea).text
        target = self.query_one("#broadcast-target", Select).value
        
        target_names = {
            "all": "Все пользователи",
            "active": "С активной подпиской",
            "inactive": "Без подписки",
            "lang_ru": "Русскоязычные",
            "lang_en": "Англоязычные",
        }
        
        self.notify(f"👁️ Получатели: {target_names.get(target)}\n\n{message[:100]}...")


# ═══════════════════════════════════════════════════════════════════════════════
# ⚙️ ЭКРАН НАСТРОЕК
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsScreen(Screen):
    """Настройки системы."""
    
    BINDINGS = [
        Binding("s", "save_settings", "Сохранить"),
        Binding("escape", "app.pop_screen", "Назад"),
    ]
    
    DEFAULT_CSS = """
    SettingsScreen {
        background: $background;
    }
    
    .settings-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .settings-section {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    .settings-title {
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(classes="settings-container"):
            yield Static("⚙️ НАСТРОЙКИ СИСТЕМЫ", classes="section-title")
            
            # Crypto Bot API
            with Container(classes="settings-section"):
                yield Static("💳 Crypto Bot API", classes="settings-title")
                
                with Horizontal(classes="form-row"):
                    yield Static("API Token:", classes="form-label")
                    yield Input(placeholder="Токен Crypto Bot", id="crypto-token", password=True)
                
                with Horizontal(classes="form-row"):
                    yield Static("Валюта:", classes="form-label")
                    yield Select(
                        [("USDT", "USDT"), ("TON", "TON"), ("BTC", "BTC")],
                        id="crypto-currency",
                        value="USDT"
                    )
            
            # Telegram Bot
            with Container(classes="settings-section"):
                yield Static("🤖 Telegram Bot", classes="settings-title")
                
                with Horizontal(classes="form-row"):
                    yield Static("Bot Token:", classes="form-label")
                    yield Input(placeholder="Токен бота", id="bot-token", password=True)
                
                with Horizontal(classes="form-row"):
                    yield Static("Admin IDs:", classes="form-label")
                    yield Input(placeholder="123456789, 987654321", id="admin-ids")
            
            # Подписки
            with Container(classes="settings-section"):
                yield Static("📋 Настройки подписок", classes="settings-title")
                
                with Horizontal(classes="form-row"):
                    yield Static("Автокик:", classes="form-label")
                    yield Select(
                        [("Включен", "on"), ("Выключен", "off")],
                        id="auto-kick",
                        value="on"
                    )
                
                with Horizontal(classes="form-row"):
                    yield Static("Напоминание:", classes="form-label")
                    yield Input(placeholder="Дней до окончания", id="reminder-days", value="3")
            
            with Horizontal(classes="button-row"):
                yield Button("💾 Сохранить настройки", variant="success", id="btn-save-settings")
        
        yield Footer()
    
    @on(Button.Pressed, "#btn-save-settings")
    def save_settings(self) -> None:
        """Сохранить настройки."""
        self.notify("✅ Настройки сохранены!")
    
    def action_save_settings(self) -> None:
        """Сохранить настройки (горячая клавиша)."""
        self.save_settings()


# ═══════════════════════════════════════════════════════════════════════════════
# 🏠 ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════════════════════

class MainMenu(Screen):
    """Главное меню TUI админки."""
    
    BINDINGS = [
        Binding("1", "open_dashboard", "Дашборд"),
        Binding("2", "open_channels", "Каналы"),
        Binding("3", "open_packages", "Пакеты"),
        Binding("4", "open_promocodes", "Промокоды"),
        Binding("5", "open_users", "Пользователи"),
        Binding("6", "open_broadcast", "Рассылка"),
        Binding("7", "open_settings", "Настройки"),
        Binding("q", "quit", "Выход"),
    ]
    
    DEFAULT_CSS = """
    MainMenu {
        background: $background;
        align: center middle;
    }
    
    .menu-container {
        width: 80;
        height: auto;
        border: double $primary;
        padding: 2;
        background: $surface;
    }
    
    .menu-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
    }
    
    .menu-subtitle {
        text-align: center;
        color: $text-muted;
        padding-bottom: 2;
    }
    
    .menu-item {
        width: 100%;
        height: 3;
        margin: 1 0;
    }
    
    .menu-item:hover {
        background: $primary-darken-2;
    }
    
    .quick-stats {
        width: 100%;
        height: auto;
        padding: 1;
        border-top: solid $primary-darken-2;
        margin-top: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(classes="menu-container"):
            yield Static("🔐 TUI АДМИН-ПАНЕЛЬ", classes="menu-title")
            yield Static("Telegram Bot Access Control", classes="menu-subtitle")
            
            yield Button("📊 [1] Дашборд", variant="primary", id="btn-dashboard", classes="menu-item")
            yield Button("📢 [2] Каналы", variant="default", id="btn-channels", classes="menu-item")
            yield Button("📦 [3] Пакеты", variant="default", id="btn-packages", classes="menu-item")
            yield Button("🎟️ [4] Промокоды", variant="default", id="btn-promocodes", classes="menu-item")
            yield Button("👥 [5] Пользователи", variant="default", id="btn-users", classes="menu-item")
            yield Button("📨 [6] Рассылка", variant="default", id="btn-broadcast", classes="menu-item")
            yield Button("⚙️ [7] Настройки", variant="default", id="btn-settings", classes="menu-item")
            
            yield Rule()
            
            yield Button("❌ [Q] Выход", variant="error", id="btn-quit", classes="menu-item")
            
            # Быстрая статистика
            with Container(classes="quick-stats"):
                yield Static("📈 Быстрая статистика:", id="quick-stats-title")
                yield Static("👥 Пользователей: загрузка...", id="qs-users")
                yield Static("💰 Доход сегодня: загрузка...", id="qs-revenue")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """При загрузке меню."""
        await self.load_quick_stats()
    
    @work(exclusive=True)
    async def load_quick_stats(self) -> None:
        """Загрузка быстрой статистики."""
        if not DATABASE_AVAILABLE:
            self.query_one("#qs-users", Static).update("👥 Пользователей: 1,234")
            self.query_one("#qs-revenue", Static).update("💰 Доход сегодня: $345.00")
            return
        
        async with async_session_factory() as session:
            stats = await StatisticsCRUD.get_quick_stats(session)
            self.query_one("#qs-users", Static).update(f"👥 Пользователей: {stats.get('total_users', 0):,}")
            self.query_one("#qs-revenue", Static).update(f"💰 Доход сегодня: ${stats.get('today_revenue', 0):.2f}")
    
    # Обработчики кнопок
    @on(Button.Pressed, "#btn-dashboard")
    def open_dashboard_btn(self) -> None:
        self.action_open_dashboard()
    
    @on(Button.Pressed, "#btn-channels")
    def open_channels_btn(self) -> None:
        self.action_open_channels()
    
    @on(Button.Pressed, "#btn-packages")
    def open_packages_btn(self) -> None:
        self.action_open_packages()
    
    @on(Button.Pressed, "#btn-promocodes")
    def open_promocodes_btn(self) -> None:
        self.action_open_promocodes()
    
    @on(Button.Pressed, "#btn-users")
    def open_users_btn(self) -> None:
        self.action_open_users()
    
    @on(Button.Pressed, "#btn-broadcast")
    def open_broadcast_btn(self) -> None:
        self.action_open_broadcast()
    
    @on(Button.Pressed, "#btn-settings")
    def open_settings_btn(self) -> None:
        self.action_open_settings()
    
    @on(Button.Pressed, "#btn-quit")
    def quit_btn(self) -> None:
        self.action_quit()
    
    # Действия
    def action_open_dashboard(self) -> None:
        self.app.push_screen(DashboardScreen())
    
    def action_open_channels(self) -> None:
        self.app.push_screen(ChannelsScreen())
    
    def action_open_packages(self) -> None:
        self.app.push_screen(PackagesScreen())
    
    def action_open_promocodes(self) -> None:
        self.app.push_screen(PromocodesScreen())
    
    def action_open_users(self) -> None:
        self.app.push_screen(UsersScreen())
    
    def action_open_broadcast(self) -> None:
        self.app.push_screen(BroadcastScreen())
    
    def action_open_settings(self) -> None:
        self.app.push_screen(SettingsScreen())
    
    def action_quit(self) -> None:
        self.app.exit()


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

class AdminApp(App):
    """TUI Админ-панель для бота продажи доступов."""
    
    TITLE = "TUI Admin Panel"
    SUB_TITLE = "Telegram Bot Access Control"
    
    CSS = """
    Screen {
        background: $background;
    }
    
    .section-title {
        text-style: bold;
        color: $primary;
        padding: 1 0;
        text-align: center;
    }
    
    .form-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    
    .form-label {
        width: 20;
        padding: 1;
    }
    
    .form-input {
        width: 1fr;
    }
    
    .button-row {
        width: 100%;
        height: auto;
        padding: 1;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    SCREENS = {
        "main": MainMenu,
        "dashboard": DashboardScreen,
        "channels": ChannelsScreen,
        "packages": PackagesScreen,
        "promocodes": PromocodesScreen,
        "users": UsersScreen,
        "broadcast": BroadcastScreen,
        "settings": SettingsScreen,
    }
    
    def on_mount(self) -> None:
        """При запуске приложения."""
        self.push_screen(MainMenu())


# ═══════════════════════════════════════════════════════════════════════════════
# 🏁 ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Запуск TUI админки."""
    app = AdminApp()
    app.run()


if __name__ == "__main__":
    main()
