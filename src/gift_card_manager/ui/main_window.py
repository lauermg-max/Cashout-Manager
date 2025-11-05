"""Qt main window scaffolding."""

from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMainWindow, QStatusBar, QTabWidget, QWidget

from ..core.settings import settings


class MainWindow(QMainWindow):
    """Top-level window for the application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(settings.app_name)
        self.resize(1280, 800)

        self._tab_widget = QTabWidget()
        self.setCentralWidget(self._tab_widget)

        self._create_tabs()
        self._create_menu()
        self._create_status_bar()

    def _create_tabs(self) -> None:
        self._tab_widget.addTab(self._placeholder_tab("Gift Card Inventory"), "Gift Cards")
        self._tab_widget.addTab(self._placeholder_tab("Orders"), "Orders")
        self._tab_widget.addTab(self._placeholder_tab("Inventory"), "Inventory")
        self._tab_widget.addTab(self._placeholder_tab("Sales"), "Sales")
        self._tab_widget.addTab(self._placeholder_tab("Accounts"), "Accounts")
        self._tab_widget.addTab(self._placeholder_tab("Analytics"), "Analytics")

    def _placeholder_tab(self, label: str) -> QWidget:
        widget = QWidget()
        layout = widget.layout()  # type: ignore[assignment]
        if layout is None:
            from PySide6.QtWidgets import QVBoxLayout

            layout = QVBoxLayout()
            widget.setLayout(layout)

        placeholder = QLabel(f"{label} view coming soon")
        placeholder.setObjectName("placeholder-label")
        placeholder.setStyleSheet("color: #666; font-size: 18px; margin: 24px;")
        layout.addWidget(placeholder)
        return widget

    def _create_menu(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _create_status_bar(self) -> None:
        status_bar = QStatusBar()
        status_bar.showMessage("Ready")
        self.setStatusBar(status_bar)

    def _show_about_dialog(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "About",
            f"{settings.app_name}\n\nLocal gift card, orders, and analytics manager.",
        )
