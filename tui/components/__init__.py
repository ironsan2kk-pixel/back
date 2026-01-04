"""
═══════════════════════════════════════════════════════════════════════════════
🖥️ КОМПОНЕНТЫ TUI
═══════════════════════════════════════════════════════════════════════════════
Модальные окна и переиспользуемые компоненты.
═══════════════════════════════════════════════════════════════════════════════
"""

from .modals import (
    ConfirmDialog,
    InputDialog,
    GiveAccessDialog,
    CreatePackageDialog,
    BulkPromoDialog,
    StatsDetailDialog,
    InfoDialog,
)

__all__ = [
    "ConfirmDialog",
    "InputDialog",
    "GiveAccessDialog",
    "CreatePackageDialog",
    "BulkPromoDialog",
    "StatsDetailDialog",
    "InfoDialog",
]
