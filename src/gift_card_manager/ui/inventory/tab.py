"""Inventory tab wrapper."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .view import InventoryView


class InventoryTab(QWidget):
    """Widget used for the Inventory tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(InventoryView(self))
        self.setLayout(layout)
