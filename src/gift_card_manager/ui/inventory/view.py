"""Inventory tab view widget."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ...core import session_scope
from ...models import InventoryItem
from ...models.enums import InventorySourceType
from ...services import InventoryAdjustment, InventoryService
from .dialogs import (
    InventoryAdjustmentDialog,
    InventoryItemDialog,
)
from .model import InventoryTableModel

logger = logging.getLogger(__name__)


@dataclass
class InventorySelection:
    rows: List[InventoryItem]

    @property
    def count(self) -> int:
        return len(self.rows)

    def ensure_single(self) -> InventoryItem | None:
        if self.count != 1:
            return None
        return self.rows[0]


class InventoryView(QWidget):
    """Composite widget for inventory management."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = InventoryTableModel()
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)

        self._search_field = QLineEdit()
        self._search_field.setPlaceholderText("Search by item name or SKU…")
        self._search_field.textChanged.connect(self._apply_search_filter)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_toolbar())
        layout.addLayout(self._build_filter_row())
        layout.addWidget(self._table)
        self.setLayout(layout)

        self.refresh()

        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

    # ------------------------------------------------------------------ UI --
    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Inventory Actions", self)
        toolbar.setMovable(False)

        add_action = toolbar.addAction("Add Item")
        add_action.triggered.connect(self._add_item)

        edit_action = toolbar.addAction("Edit Item")
        edit_action.triggered.connect(self._edit_selected)

        delete_action = toolbar.addAction("Delete Item")
        delete_action.triggered.connect(self._delete_selected)

        toolbar.addSeparator()

        adjust_action = toolbar.addAction("Adjust Stock")
        adjust_action.triggered.connect(self._adjust_selected)

        toolbar.addSeparator()

        refresh_action = toolbar.addAction("Refresh")
        refresh_action.triggered.connect(self.refresh)

        return toolbar

    def _build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(8, 4, 8, 4)
        row.addWidget(QLabel("Search:"))
        row.addWidget(self._search_field, 2)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._search_field.clear)
        row.addWidget(clear_button)
        row.addStretch(1)
        return row

    # -------------------------------------------------------------- Data ----
    def refresh(self) -> None:
        with session_scope() as session:
            items = self._load_inventory(session)
        self._model.set_rows(items)
        self._apply_search_filter(self._search_field.text())

    def _load_inventory(self, session) -> Iterable[InventoryItem]:
        return session.query(InventoryItem).order_by(InventoryItem.item_name).all()

    # ---------------------------------------------------------- Search ------
    def _apply_search_filter(self, text: str) -> None:
        text = text.strip().lower()
        selection_model = self._table.selectionModel()
        selection_model.clearSelection()

        if not text:
            self._table.viewport().update()
            return

        for row_index, item in enumerate(self._model.all_rows()):
            if text in (item.item_name or "").lower() or text in (item.sku or "").lower():
                index = self._model.index(row_index, 0)
                selection_model.select(index, selection_model.Select | selection_model.Rows)

    # ---------------------------------------------------- Context menu -----
    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Add Item", self._add_item)
        selection = self._current_selection()
        if selection.count:
            menu.addSeparator()
            menu.addAction("Edit Item", self._edit_selected)
            menu.addAction("Delete Item", self._delete_selected)
            menu.addSeparator()
            menu.addAction("Adjust Stock", self._adjust_selected)
        menu.exec(self._table.viewport().mapToGlobal(position))

    # ------------------------------------------------------------ Actions ---
    def _add_item(self) -> None:
        dialog = InventoryItemDialog(parent=self)
        if dialog.exec() != InventoryItemDialog.Accepted:
            return

        result = dialog.result_data()
        if result is None:
            return

        item = InventoryItem(
            item_name=result.item_name,
            sku=result.sku,
            upc=result.upc,
            quantity_on_hand=result.quantity_on_hand,
            average_cost=result.average_cost,
            total_cost=result.total_cost,
        )

        with session_scope() as session:
            service = InventoryService(session)
            try:
                initial_adjustment = None
                if result.quantity_on_hand or result.total_cost:
                    cost_change = result.total_cost - Decimal(result.quantity_on_hand) * result.average_cost
                    initial_adjustment = InventoryAdjustment(
                        quantity_change=result.quantity_on_hand,
                        cost_change=result.total_cost,
                        source_type=InventorySourceType.ADJUSTMENT,
                        notes="Initial stock",
                    )
                service.create_item(item, initial_adjustment=initial_adjustment)
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to create inventory item")
                QMessageBox.critical(self, "Add Item", f"Failed to create item:\n{exc}")
                return

        self.refresh()

    def _edit_selected(self) -> None:
        selection = self._current_selection()
        item = selection.ensure_single()
        if item is None:
            QMessageBox.information(self, "Edit Item", "Select one inventory item to edit.")
            return

        dialog = InventoryItemDialog(parent=self, existing=item)
        if dialog.exec() != InventoryItemDialog.Accepted:
            return

        result = dialog.result_data()
        if result is None:
            return

        with session_scope() as session:
            db_item = session.get(InventoryItem, item.id)
            if db_item is None:
                QMessageBox.warning(self, "Edit Item", "Selected item no longer exists.")
                return

            db_item.item_name = result.item_name
            db_item.sku = result.sku
            db_item.upc = result.upc
            db_item.quantity_on_hand = result.quantity_on_hand
            db_item.average_cost = result.average_cost
            db_item.total_cost = result.total_cost

            service = InventoryService(session)

            try:
                service.update_item(db_item)
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to update inventory item")
                QMessageBox.critical(self, "Edit Item", f"Failed to update item:\n{exc}")
                return

        self.refresh()

    def _delete_selected(self) -> None:
        selection = self._current_selection()
        if selection.count == 0:
            QMessageBox.information(self, "Delete Items", "No items selected.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Items",
            f"Delete {selection.count} selected item(s)? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        with session_scope() as session:
            service = InventoryService(session)
            for item in selection.rows:
                db_item = session.get(InventoryItem, item.id)
                if db_item:
                    service.delete_item(db_item)
            try:
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to delete inventory items")
                QMessageBox.critical(self, "Delete Items", f"Failed to delete items:\n{exc}")
                return

        self.refresh()

    def _adjust_selected(self) -> None:
        selection = self._current_selection()
        item = selection.ensure_single()
        if item is None:
            QMessageBox.information(self, "Adjust Stock", "Select one item to adjust.")
            return

        dialog = InventoryAdjustmentDialog(parent=self)
        if dialog.exec() != InventoryAdjustmentDialog.Accepted:
            return

        result = dialog.result_data()
        if result is None:
            return

        with session_scope() as session:
            db_item = session.get(InventoryItem, item.id)
            if db_item is None:
                QMessageBox.warning(self, "Adjust Stock", "Selected item no longer exists.")
                return

            service = InventoryService(session)

            try:
                service.apply_adjustment(db_item, result.adjustment)
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to apply inventory adjustment")
                QMessageBox.critical(self, "Adjust Stock", f"Failed to apply adjustment:\n{exc}")
                return

        self.refresh()

    # --------------------------------------------------------- Helpers ------
    def _current_selection(self) -> InventorySelection:
        selection_model = self._table.selectionModel()
        selected_rows = selection_model.selectedRows()
        rows: List[InventoryItem] = []
        for index in selected_rows:
            rows.append(self._model.row_at(index.row()))
        return InventorySelection(rows)
