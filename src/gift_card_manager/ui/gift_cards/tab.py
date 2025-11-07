"""Gift card inventory tab."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .view import GiftCardInventoryView


class GiftCardInventoryTab(QWidget):
    """Wrapper widget used as the Gift Cards tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(GiftCardInventoryView(self))
        self.setLayout(layout)
