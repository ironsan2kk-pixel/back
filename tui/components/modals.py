"""
═══════════════════════════════════════════════════════════════════════════════
🖥️ МОДАЛЬНЫЕ ОКНА
═══════════════════════════════════════════════════════════════════════════════
Диалоговые окна и модальные формы для TUI админки.
═══════════════════════════════════════════════════════════════════════════════
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.screen import ModalScreen
from textual.widgets import (
    Static, 
    Button, 
    Input, 
    Select, 
    Label,
    TextArea,
    DataTable,
)
from textual import on
from typing import Optional, Callable, Any


# ═══════════════════════════════════════════════════════════════════════════════
# ❓ ДИАЛОГ ПОДТВЕРЖДЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

class ConfirmDialog(ModalScreen[bool]):
    """Диалог подтверждения действия."""
    
    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }
    
    ConfirmDialog > Container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    ConfirmDialog .dialog-title {
        text-style: bold;
        color: $warning;
        text-align: center;
        padding-bottom: 1;
    }
    
    ConfirmDialog .dialog-message {
        text-align: center;
        padding: 1;
    }
    
    ConfirmDialog .dialog-buttons {
        align: center middle;
        padding-top: 1;
    }
    
    ConfirmDialog Button {
        margin: 0 2;
    }
    """
    
    def __init__(
        self,
        title: str = "Подтверждение",
        message: str = "Вы уверены?",
        confirm_text: str = "✅ Да",
        cancel_text: str = "❌ Нет",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.title_text = title
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"⚠️ {self.title_text}", classes="dialog-title")
            yield Static(self.message, classes="dialog-message")
            
            with Horizontal(classes="dialog-buttons"):
                yield Button(self.confirm_text, variant="success", id="btn-confirm")
                yield Button(self.cancel_text, variant="error", id="btn-cancel")
    
    @on(Button.Pressed, "#btn-confirm")
    def confirm(self) -> None:
        """Подтверждение."""
        self.dismiss(True)
    
    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        """Отмена."""
        self.dismiss(False)


# ═══════════════════════════════════════════════════════════════════════════════
# 📝 ДИАЛОГ ВВОДА
# ═══════════════════════════════════════════════════════════════════════════════

class InputDialog(ModalScreen[Optional[str]]):
    """Диалог с полем ввода."""
    
    DEFAULT_CSS = """
    InputDialog {
        align: center middle;
    }
    
    InputDialog > Container {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    InputDialog .dialog-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding-bottom: 1;
    }
    
    InputDialog .dialog-label {
        padding: 1 0;
    }
    
    InputDialog Input {
        width: 100%;
        margin-bottom: 1;
    }
    
    InputDialog .dialog-buttons {
        align: center middle;
        padding-top: 1;
    }
    """
    
    def __init__(
        self,
        title: str = "Ввод данных",
        label: str = "Введите значение:",
        placeholder: str = "",
        default_value: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.title_text = title
        self.label = label
        self.placeholder = placeholder
        self.default_value = default_value
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"📝 {self.title_text}", classes="dialog-title")
            yield Static(self.label, classes="dialog-label")
            yield Input(
                placeholder=self.placeholder, 
                value=self.default_value,
                id="input-value"
            )
            
            with Horizontal(classes="dialog-buttons"):
                yield Button("💾 Сохранить", variant="success", id="btn-save")
                yield Button("❌ Отмена", variant="error", id="btn-cancel")
    
    @on(Button.Pressed, "#btn-save")
    def save(self) -> None:
        """Сохранение."""
        value = self.query_one("#input-value", Input).value
        self.dismiss(value)
    
    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        """Отмена."""
        self.dismiss(None)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎁 ДИАЛОГ ВЫДАЧИ ДОСТУПА
# ═══════════════════════════════════════════════════════════════════════════════

class GiveAccessDialog(ModalScreen[Optional[dict]]):
    """Диалог выдачи доступа пользователю."""
    
    DEFAULT_CSS = """
    GiveAccessDialog {
        align: center middle;
    }
    
    GiveAccessDialog > Container {
        width: 80;
        height: auto;
        border: thick $success;
        background: $surface;
        padding: 1 2;
    }
    
    GiveAccessDialog .dialog-title {
        text-style: bold;
        color: $success;
        text-align: center;
        padding-bottom: 1;
    }
    
    GiveAccessDialog .form-row {
        width: 100%;
        height: auto;
        padding: 1 0;
    }
    
    GiveAccessDialog .form-label {
        width: 20;
    }
    
    GiveAccessDialog Select, GiveAccessDialog Input {
        width: 1fr;
    }
    
    GiveAccessDialog .dialog-buttons {
        align: center middle;
        padding-top: 1;
    }
    """
    
    def __init__(self, user_id: int, username: str = "", **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.username = username
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"🎁 Выдача доступа: {self.username or self.user_id}", classes="dialog-title")
            
            with Horizontal(classes="form-row"):
                yield Static("Тип:", classes="form-label")
                yield Select(
                    [
                        ("Канал", "channel"),
                        ("Пакет", "package"),
                    ],
                    id="access-type",
                    value="channel"
                )
            
            with Horizontal(classes="form-row"):
                yield Static("Канал/Пакет:", classes="form-label")
                yield Select(
                    [
                        ("VIP Канал", "1"),
                        ("Premium", "2"),
                        ("Базовый пакет", "pkg_1"),
                    ],
                    id="access-target"
                )
            
            with Horizontal(classes="form-row"):
                yield Static("Срок (дней):", classes="form-label")
                yield Select(
                    [
                        ("30 дней", "30"),
                        ("90 дней", "90"),
                        ("365 дней", "365"),
                        ("Навсегда", "0"),
                    ],
                    id="access-duration",
                    value="30"
                )
            
            with Horizontal(classes="form-row"):
                yield Static("Причина:", classes="form-label")
                yield Input(placeholder="Подарок / Компенсация / Тест", id="access-reason")
            
            with Horizontal(classes="dialog-buttons"):
                yield Button("🎁 Выдать", variant="success", id="btn-give")
                yield Button("❌ Отмена", variant="error", id="btn-cancel")
    
    @on(Button.Pressed, "#btn-give")
    def give_access(self) -> None:
        """Выдать доступ."""
        result = {
            "user_id": self.user_id,
            "type": self.query_one("#access-type", Select).value,
            "target": self.query_one("#access-target", Select).value,
            "duration": int(self.query_one("#access-duration", Select).value),
            "reason": self.query_one("#access-reason", Input).value,
        }
        self.dismiss(result)
    
    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        """Отмена."""
        self.dismiss(None)


# ═══════════════════════════════════════════════════════════════════════════════
# 📦 ДИАЛОГ СОЗДАНИЯ ПАКЕТА
# ═══════════════════════════════════════════════════════════════════════════════

class CreatePackageDialog(ModalScreen[Optional[dict]]):
    """Диалог создания нового пакета."""
    
    DEFAULT_CSS = """
    CreatePackageDialog {
        align: center middle;
    }
    
    CreatePackageDialog > Container {
        width: 90;
        height: auto;
        max-height: 90%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
        overflow-y: auto;
    }
    
    CreatePackageDialog .dialog-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding-bottom: 1;
    }
    
    CreatePackageDialog .section-title {
        text-style: bold;
        color: $secondary;
        padding: 1 0;
    }
    
    CreatePackageDialog .form-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    
    CreatePackageDialog .form-label {
        width: 20;
    }
    
    CreatePackageDialog Input {
        width: 1fr;
    }
    
    CreatePackageDialog .channels-grid {
        width: 100%;
        height: auto;
        padding: 1;
        border: solid $primary-darken-2;
    }
    
    CreatePackageDialog .dialog-buttons {
        align: center middle;
        padding-top: 1;
    }
    """
    
    def __init__(self, available_channels: list = None, **kwargs):
        super().__init__(**kwargs)
        self.available_channels = available_channels or [
            {"id": 1, "name": "VIP Канал"},
            {"id": 2, "name": "Premium Content"},
            {"id": 3, "name": "Exclusive News"},
        ]
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("📦 Создание пакета", classes="dialog-title")
            
            # Основная информация
            yield Static("📋 Основная информация", classes="section-title")
            
            with Horizontal(classes="form-row"):
                yield Static("Название:", classes="form-label")
                yield Input(placeholder="Название пакета", id="pkg-name")
            
            with Horizontal(classes="form-row"):
                yield Static("Описание RU:", classes="form-label")
                yield Input(placeholder="Описание на русском", id="pkg-desc-ru")
            
            with Horizontal(classes="form-row"):
                yield Static("Описание EN:", classes="form-label")
                yield Input(placeholder="Description in English", id="pkg-desc-en")
            
            # Цены
            yield Static("💰 Цены (USDT)", classes="section-title")
            
            with Horizontal(classes="form-row"):
                yield Static("30 дней:", classes="form-label")
                yield Input(placeholder="9.99", id="pkg-price-30")
            
            with Horizontal(classes="form-row"):
                yield Static("90 дней:", classes="form-label")
                yield Input(placeholder="24.99", id="pkg-price-90")
            
            with Horizontal(classes="form-row"):
                yield Static("365 дней:", classes="form-label")
                yield Input(placeholder="79.99", id="pkg-price-365")
            
            # Каналы
            yield Static("📢 Каналы в пакете", classes="section-title")
            yield Static("(Выберите каналы в таблице)", classes="form-label")
            
            yield DataTable(id="channels-table", classes="channels-grid")
            
            with Horizontal(classes="dialog-buttons"):
                yield Button("💾 Создать", variant="success", id="btn-create")
                yield Button("❌ Отмена", variant="error", id="btn-cancel")
    
    async def on_mount(self) -> None:
        """При загрузке диалога."""
        table = self.query_one("#channels-table", DataTable)
        table.add_columns("✓", "ID", "Название")
        table.cursor_type = "row"
        
        for ch in self.available_channels:
            table.add_row("☐", str(ch["id"]), ch["name"])
    
    @on(DataTable.RowSelected, "#channels-table")
    def toggle_channel(self, event: DataTable.RowSelected) -> None:
        """Переключение выбора канала."""
        table = event.data_table
        row_key = event.row_key
        current = table.get_cell(row_key, "✓")
        new_value = "☑" if current == "☐" else "☐"
        table.update_cell(row_key, "✓", new_value)
    
    @on(Button.Pressed, "#btn-create")
    def create_package(self) -> None:
        """Создать пакет."""
        table = self.query_one("#channels-table", DataTable)
        
        # Собираем выбранные каналы
        selected_channels = []
        for row_key in table.rows:
            row = table.get_row(row_key)
            if row[0] == "☑":
                selected_channels.append(int(row[1]))
        
        result = {
            "name": self.query_one("#pkg-name", Input).value,
            "description_ru": self.query_one("#pkg-desc-ru", Input).value,
            "description_en": self.query_one("#pkg-desc-en", Input).value,
            "prices": {
                30: float(self.query_one("#pkg-price-30", Input).value or 0),
                90: float(self.query_one("#pkg-price-90", Input).value or 0),
                365: float(self.query_one("#pkg-price-365", Input).value or 0),
            },
            "channels": selected_channels,
        }
        self.dismiss(result)
    
    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        """Отмена."""
        self.dismiss(None)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎟️ ДИАЛОГ МАССОВОЙ ГЕНЕРАЦИИ ПРОМОКОДОВ
# ═══════════════════════════════════════════════════════════════════════════════

class BulkPromoDialog(ModalScreen[Optional[dict]]):
    """Диалог массовой генерации промокодов."""
    
    DEFAULT_CSS = """
    BulkPromoDialog {
        align: center middle;
    }
    
    BulkPromoDialog > Container {
        width: 70;
        height: auto;
        border: thick $warning;
        background: $surface;
        padding: 1 2;
    }
    
    BulkPromoDialog .dialog-title {
        text-style: bold;
        color: $warning;
        text-align: center;
        padding-bottom: 1;
    }
    
    BulkPromoDialog .form-row {
        width: 100%;
        height: auto;
        padding: 1 0;
    }
    
    BulkPromoDialog .form-label {
        width: 25;
    }
    
    BulkPromoDialog Select, BulkPromoDialog Input {
        width: 1fr;
    }
    
    BulkPromoDialog .dialog-buttons {
        align: center middle;
        padding-top: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("🎲 Массовая генерация промокодов", classes="dialog-title")
            
            with Horizontal(classes="form-row"):
                yield Static("Количество:", classes="form-label")
                yield Input(placeholder="10", value="10", id="promo-count")
            
            with Horizontal(classes="form-row"):
                yield Static("Префикс:", classes="form-label")
                yield Input(placeholder="PROMO", value="PROMO", id="promo-prefix")
            
            with Horizontal(classes="form-row"):
                yield Static("Тип скидки:", classes="form-label")
                yield Select(
                    [
                        ("Процент", "percent"),
                        ("Фиксированная сумма", "fixed"),
                        ("Бесплатный доступ", "free"),
                    ],
                    id="promo-type",
                    value="percent"
                )
            
            with Horizontal(classes="form-row"):
                yield Static("Значение скидки:", classes="form-label")
                yield Input(placeholder="50", value="50", id="promo-value")
            
            with Horizontal(classes="form-row"):
                yield Static("Использований каждый:", classes="form-label")
                yield Input(placeholder="1 (0 = безлимит)", value="1", id="promo-uses")
            
            with Horizontal(classes="dialog-buttons"):
                yield Button("🎲 Генерировать", variant="warning", id="btn-generate")
                yield Button("❌ Отмена", variant="error", id="btn-cancel")
    
    @on(Button.Pressed, "#btn-generate")
    def generate(self) -> None:
        """Генерация промокодов."""
        result = {
            "count": int(self.query_one("#promo-count", Input).value or 10),
            "prefix": self.query_one("#promo-prefix", Input).value or "PROMO",
            "type": self.query_one("#promo-type", Select).value,
            "value": float(self.query_one("#promo-value", Input).value or 0),
            "max_uses": int(self.query_one("#promo-uses", Input).value or 1),
        }
        self.dismiss(result)
    
    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        """Отмена."""
        self.dismiss(None)


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ДИАЛОГ ДЕТАЛЬНОЙ СТАТИСТИКИ
# ═══════════════════════════════════════════════════════════════════════════════

class StatsDetailDialog(ModalScreen):
    """Диалог с детальной статистикой."""
    
    DEFAULT_CSS = """
    StatsDetailDialog {
        align: center middle;
    }
    
    StatsDetailDialog > Container {
        width: 90;
        height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    StatsDetailDialog .dialog-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding-bottom: 1;
    }
    
    StatsDetailDialog DataTable {
        width: 100%;
        height: 1fr;
        border: solid $primary-darken-2;
    }
    
    StatsDetailDialog .dialog-buttons {
        align: center middle;
        padding-top: 1;
    }
    """
    
    def __init__(self, title: str, data: list, columns: list, **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.data = data
        self.columns = columns
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"📊 {self.title_text}", classes="dialog-title")
            yield DataTable(id="stats-table")
            
            with Horizontal(classes="dialog-buttons"):
                yield Button("📥 Экспорт CSV", variant="primary", id="btn-export")
                yield Button("❌ Закрыть", variant="error", id="btn-close")
    
    async def on_mount(self) -> None:
        """При загрузке диалога."""
        table = self.query_one("#stats-table", DataTable)
        table.add_columns(*self.columns)
        
        for row in self.data:
            table.add_row(*row)
    
    @on(Button.Pressed, "#btn-export")
    def export_csv(self) -> None:
        """Экспорт в CSV."""
        self.app.notify("📥 Экспорт в CSV: функция будет добавлена")
    
    @on(Button.Pressed, "#btn-close")
    def close(self) -> None:
        """Закрыть."""
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════════════
# ℹ️ ИНФОРМАЦИОННЫЙ ДИАЛОГ
# ═══════════════════════════════════════════════════════════════════════════════

class InfoDialog(ModalScreen):
    """Информационный диалог."""
    
    DEFAULT_CSS = """
    InfoDialog {
        align: center middle;
    }
    
    InfoDialog > Container {
        width: 60;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    
    InfoDialog .dialog-title {
        text-style: bold;
        color: $accent;
        text-align: center;
        padding-bottom: 1;
    }
    
    InfoDialog .dialog-message {
        text-align: center;
        padding: 1;
    }
    
    InfoDialog .dialog-buttons {
        align: center middle;
        padding-top: 1;
    }
    """
    
    def __init__(self, title: str, message: str, **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"ℹ️ {self.title_text}", classes="dialog-title")
            yield Static(self.message, classes="dialog-message")
            
            with Horizontal(classes="dialog-buttons"):
                yield Button("✅ OK", variant="primary", id="btn-ok")
    
    @on(Button.Pressed, "#btn-ok")
    def close(self) -> None:
        """Закрыть."""
        self.dismiss()
