"""Analytics tab wrapper."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .view import AnalyticsView


class AnalyticsTab(QWidget):
    """Widget used for the Analytics tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(AnalyticsView(self))
        self.setLayout(layout)
