"""
═══════════════════════════════════════════════════════════════════════════════
🖥️ КАСТОМНЫЕ ВИДЖЕТЫ
═══════════════════════════════════════════════════════════════════════════════
Переиспользуемые виджеты для TUI админки.
═══════════════════════════════════════════════════════════════════════════════
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Button, DataTable, ProgressBar, Sparkline
from textual.reactive import reactive
from textual import on

from rich.text import Text
from rich.table import Table
from rich.panel import Panel

from datetime import datetime
from typing import Optional, List, Dict, Any


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ВИДЖЕТ СТАТИСТИКИ
# ═══════════════════════════════════════════════════════════════════════════════

class StatCard(Static):
    """Карточка со статистикой."""
    
    DEFAULT_CSS = """
    StatCard {
        width: 1fr;
        height: 7;
        border: round $primary;
        padding: 1;
        margin: 0 1;
        background: $surface;
    }
    
    StatCard:hover {
        border: round $accent;
        background: $surface-lighten-1;
    }
    
    StatCard.positive .stat-change {
        color: $success;
    }
    
    StatCard.negative .stat-change {
        color: $error;
    }
    """
    
    value = reactive("0")
    change = reactive("")
    
    def __init__(
        self,
        title: str,
        value: str = "0",
        change: str = "",
        icon: str = "📊",
        positive: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.change = change
        self.icon = icon
        self._positive = positive
        
        if positive:
            self.add_class("positive")
        else:
            self.add_class("negative")
    
    def compose(self) -> ComposeResult:
        yield Static(f"{self.icon} {self.title}", classes="stat-title")
        yield Static(self.value, classes="stat-value")
        if self.change:
            yield Static(self.change, classes="stat-change")
    
    def update_value(self, value: str, change: str = "", positive: bool = True):
        """Обновить значение карточки."""
        self.value = value
        self.change = change
        
        self.remove_class("positive")
        self.remove_class("negative")
        if positive:
            self.add_class("positive")
        else:
            self.add_class("negative")
        
        self.refresh()


# ═══════════════════════════════════════════════════════════════════════════════
# 📈 ВИДЖЕТ ГРАФИКА
# ═══════════════════════════════════════════════════════════════════════════════

class MiniChart(Static):
    """Мини-график (спарклайн)."""
    
    DEFAULT_CSS = """
    MiniChart {
        width: 1fr;
        height: 5;
        border: solid $primary-darken-2;
        padding: 0 1;
        background: $surface;
    }
    
    MiniChart .chart-title {
        text-style: bold;
        color: $text-muted;
    }
    """
    
    def __init__(self, title: str, data: List[float] = None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.data = data or [0]
    
    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="chart-title")
        yield Sparkline(self.data, summary_function=max)
    
    def update_data(self, data: List[float]):
        """Обновить данные графика."""
        self.data = data
        sparkline = self.query_one(Sparkline)
        sparkline.data = data


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ВИДЖЕТ СПИСКА ДЕЙСТВИЙ
# ═══════════════════════════════════════════════════════════════════════════════

class ActionList(Static):
    """Список быстрых действий."""
    
    DEFAULT_CSS = """
    ActionList {
        width: 100%;
        height: auto;
        border: solid $secondary;
        padding: 1;
        background: $surface;
    }
    
    ActionList .action-title {
        text-style: bold;
        color: $secondary;
        padding-bottom: 1;
    }
    
    ActionList Button {
        width: 100%;
        margin: 1 0;
    }
    """
    
    def __init__(self, title: str, actions: List[Dict], **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.actions = actions  # [{"id": "act1", "label": "Action 1", "variant": "primary"}]
    
    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="action-title")
        
        for action in self.actions:
            yield Button(
                action.get("label", "Action"),
                variant=action.get("variant", "default"),
                id=action.get("id", "action")
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 📝 ВИДЖЕТ ПОСЛЕДНИХ СОБЫТИЙ
# ═══════════════════════════════════════════════════════════════════════════════

class RecentEvents(Static):
    """Список последних событий."""
    
    DEFAULT_CSS = """
    RecentEvents {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        padding: 1;
        background: $surface;
    }
    
    RecentEvents .events-title {
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
    }
    
    RecentEvents .event-item {
        padding: 0 1;
        border-bottom: solid $primary-darken-3;
    }
    
    RecentEvents .event-time {
        color: $text-muted;
    }
    
    RecentEvents .event-text {
        color: $text;
    }
    """
    
    def __init__(self, title: str, events: List[Dict] = None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.events = events or []  # [{"time": "10:30", "text": "New user", "icon": "👤"}]
    
    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="events-title")
        
        for event in self.events[:10]:  # Максимум 10 событий
            with Container(classes="event-item"):
                yield Static(
                    f"{event.get('icon', '•')} [{event.get('time', '')}] {event.get('text', '')}",
                    classes="event-text"
                )
    
    def add_event(self, text: str, icon: str = "•"):
        """Добавить новое событие."""
        self.events.insert(0, {
            "time": datetime.now().strftime("%H:%M"),
            "text": text,
            "icon": icon
        })
        self.events = self.events[:10]  # Оставляем только последние 10
        self.refresh()


# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 ВИДЖЕТ ПОИСКА
# ═══════════════════════════════════════════════════════════════════════════════

class SearchBar(Static):
    """Панель поиска."""
    
    DEFAULT_CSS = """
    SearchBar {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    SearchBar Horizontal {
        width: 100%;
    }
    
    SearchBar Input {
        width: 1fr;
    }
    
    SearchBar Button {
        width: auto;
        margin-left: 1;
    }
    """
    
    def __init__(
        self,
        placeholder: str = "Поиск...",
        search_id: str = "search-input",
        button_id: str = "search-btn",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.placeholder = placeholder
        self.search_id = search_id
        self.button_id = button_id
    
    def compose(self) -> ComposeResult:
        from textual.widgets import Input
        
        with Horizontal():
            yield Input(placeholder=self.placeholder, id=self.search_id)
            yield Button("🔍 Поиск", variant="primary", id=self.button_id)
    
    def get_value(self) -> str:
        """Получить значение поиска."""
        from textual.widgets import Input
        return self.query_one(f"#{self.search_id}", Input).value
    
    def clear(self):
        """Очистить поле поиска."""
        from textual.widgets import Input
        self.query_one(f"#{self.search_id}", Input).value = ""


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ВИДЖЕТ ПРОГРЕСС-БАРА С ЛЕЙБЛОМ
# ═══════════════════════════════════════════════════════════════════════════════

class LabeledProgress(Static):
    """Прогресс-бар с подписью."""
    
    DEFAULT_CSS = """
    LabeledProgress {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    LabeledProgress .progress-label {
        text-align: center;
        padding-bottom: 1;
    }
    
    LabeledProgress ProgressBar {
        width: 100%;
    }
    
    LabeledProgress .progress-status {
        text-align: center;
        padding-top: 1;
        color: $text-muted;
    }
    """
    
    progress = reactive(0)
    status = reactive("")
    
    def __init__(
        self,
        label: str,
        total: int = 100,
        progress: int = 0,
        status: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.label = label
        self.total = total
        self.progress = progress
        self.status = status
    
    def compose(self) -> ComposeResult:
        yield Static(self.label, classes="progress-label")
        yield ProgressBar(total=self.total, id="progress-bar")
        yield Static(self.status, classes="progress-status", id="progress-status")
    
    def update_progress(self, progress: int, status: str = ""):
        """Обновить прогресс."""
        self.progress = progress
        self.status = status
        
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.update(progress=progress)
        
        if status:
            self.query_one("#progress-status", Static).update(status)


# ═══════════════════════════════════════════════════════════════════════════════
# 📑 ВИДЖЕТ ТАБОВ
# ═══════════════════════════════════════════════════════════════════════════════

class TabButton(Button):
    """Кнопка-таб."""
    
    DEFAULT_CSS = """
    TabButton {
        width: auto;
        min-width: 15;
        margin: 0 1;
        border: none;
        background: $surface;
    }
    
    TabButton:hover {
        background: $surface-lighten-1;
    }
    
    TabButton.active {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    """
    
    active = reactive(False)
    
    def __init__(self, label: str, tab_id: str, active: bool = False, **kwargs):
        super().__init__(label, **kwargs)
        self.tab_id = tab_id
        self.active = active
        
        if active:
            self.add_class("active")
    
    def set_active(self, active: bool):
        """Установить активность."""
        self.active = active
        if active:
            self.add_class("active")
        else:
            self.remove_class("active")


class TabBar(Static):
    """Панель табов."""
    
    DEFAULT_CSS = """
    TabBar {
        width: 100%;
        height: auto;
        padding: 1;
        border-bottom: solid $primary;
    }
    
    TabBar Horizontal {
        width: 100%;
    }
    """
    
    def __init__(self, tabs: List[Dict], active_tab: str = None, **kwargs):
        super().__init__(**kwargs)
        self.tabs = tabs  # [{"id": "tab1", "label": "Tab 1"}]
        self.active_tab = active_tab or (tabs[0]["id"] if tabs else None)
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            for tab in self.tabs:
                yield TabButton(
                    tab["label"],
                    tab_id=tab["id"],
                    active=(tab["id"] == self.active_tab),
                    id=f"tab-{tab['id']}"
                )
    
    def set_active(self, tab_id: str):
        """Установить активный таб."""
        for tab in self.tabs:
            btn = self.query_one(f"#tab-{tab['id']}", TabButton)
            btn.set_active(tab["id"] == tab_id)
        self.active_tab = tab_id


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 ВИДЖЕТ ИНФОРМАЦИОННОЙ ПАНЕЛИ
# ═══════════════════════════════════════════════════════════════════════════════

class InfoPanel(Static):
    """Информационная панель."""
    
    DEFAULT_CSS = """
    InfoPanel {
        width: 100%;
        height: auto;
        border: solid $accent;
        padding: 1;
        background: $surface;
        margin: 1 0;
    }
    
    InfoPanel.info {
        border: solid $accent;
    }
    
    InfoPanel.warning {
        border: solid $warning;
    }
    
    InfoPanel.error {
        border: solid $error;
    }
    
    InfoPanel.success {
        border: solid $success;
    }
    
    InfoPanel .panel-icon {
        text-style: bold;
    }
    
    InfoPanel .panel-text {
        padding-left: 2;
    }
    """
    
    def __init__(
        self,
        message: str,
        level: str = "info",  # info, warning, error, success
        **kwargs
    ):
        super().__init__(**kwargs)
        self.message = message
        self.level = level
        
        self.add_class(level)
        
        self.icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }
    
    def compose(self) -> ComposeResult:
        icon = self.icons.get(self.level, "ℹ️")
        yield Static(f"{icon} {self.message}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🏷️ ВИДЖЕТ ТЕГОВ
# ═══════════════════════════════════════════════════════════════════════════════

class TagList(Static):
    """Список тегов."""
    
    DEFAULT_CSS = """
    TagList {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    TagList Horizontal {
        width: 100%;
    }
    
    TagList .tag {
        background: $primary;
        color: $text;
        padding: 0 1;
        margin: 0 1;
        border: round $primary-lighten-1;
    }
    """
    
    def __init__(self, tags: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.tags = tags or []
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            for tag in self.tags:
                yield Static(tag, classes="tag")
    
    def set_tags(self, tags: List[str]):
        """Установить теги."""
        self.tags = tags
        self.refresh()
