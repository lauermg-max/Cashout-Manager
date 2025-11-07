"""Orders tab wrapper."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .view import OrdersView


class OrdersTab(QWidget):
    """Widget used for the Orders tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(OrdersView(self))
        self.setLayout(layout)
