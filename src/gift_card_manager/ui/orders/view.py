"""Orders tab view widget."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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

from sqlalchemy.orm import selectinload

from ...core import session_scope
from ...models import Order, OrderItem, Retailer
from ...services import OrderService
from .dialogs import OrderDialog
from .model import OrdersTableModel

logger = logging.getLogger(__name__)


@dataclass
class OrderSelection:
    rows: List[Order]

    @property
    def count(self) -> int:
        return len(self.rows)

    def ensure_single(self) -> Order | None:
        if self.count != 1:
            return None
        return self.rows[0]


class OrdersView(QWidget):
    """Composite widget for order management."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = OrdersTableModel()
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.ExtendedSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)

        self._retailer_filter = QComboBox()
        self._retailer_filter.currentIndexChanged.connect(self.refresh)

        self._search_field = QLineEdit()
        self._search_field.setPlaceholderText("Search by order number…")
        self._search_field.textChanged.connect(self._apply_search_filter)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_toolbar())
        layout.addLayout(self._build_filter_row())
        layout.addWidget(self._table)
        self.setLayout(layout)

        self._load_retailers()
        self.refresh()

        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

    # ------------------------------------------------------------------ UI --
    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Order Actions", self)
        toolbar.setMovable(False)

        add_action = toolbar.addAction("Add")
        add_action.triggered.connect(self._add_order)

        edit_action = toolbar.addAction("Edit")
        edit_action.triggered.connect(self._edit_selected)

        delete_action = toolbar.addAction("Delete")
        delete_action.triggered.connect(self._delete_selected)

        toolbar.addSeparator()

        refresh_action = toolbar.addAction("Refresh")
        refresh_action.triggered.connect(self.refresh)

        toolbar.addSeparator()

        export_action = toolbar.addAction("Export CSV…")
        export_action.triggered.connect(self._export_csv)

        import_action = toolbar.addAction("Import CSV…")
        import_action.triggered.connect(self._import_csv)

        return toolbar

    def _build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(8, 4, 8, 4)
        row.addWidget(QLabel("Retailer:"))
        row.addWidget(self._retailer_filter, 1)
        row.addSpacing(16)
        row.addWidget(QLabel("Search:"))
        row.addWidget(self._search_field, 2)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._search_field.clear)
        row.addWidget(clear_button)
        return row

    # -------------------------------------------------------------- Data ----
    def refresh(self) -> None:
        with session_scope() as session:
            orders = self._load_orders(session)
        self._model.set_rows(orders)
        self._apply_search_filter(self._search_field.text())

    def _load_orders(self, session) -> Iterable[Order]:
        query = (
            session.query(Order)
            .options(
                selectinload(Order.retailer),
                selectinload(Order.items),
            )
            .order_by(Order.order_date.desc(), Order.id.desc())
        )
        retailer_code = self._current_retailer_code()
        if retailer_code != "ALL":
            retailer = (
                session.query(Retailer)
                .filter(Retailer.code == retailer_code)
                .one_or_none()
            )
            if not retailer:
                return []
            query = query.filter(Order.retailer_id == retailer.id)
        return query.all()

    def _load_retailers(self) -> None:
        self._retailer_filter.blockSignals(True)
        self._retailer_filter.clear()
        self._retailer_filter.addItem("All Retailers", "ALL")
        with session_scope() as session:
            retailers = session.query(Retailer).order_by(Retailer.name).all()
        for retailer in retailers:
            self._retailer_filter.addItem(f"{retailer.name} ({retailer.code})", retailer.code)
        self._retailer_filter.blockSignals(False)

    def _current_retailer_code(self) -> str:
        return self._retailer_filter.currentData(Qt.ItemDataRole.UserRole) or "ALL"

    # ---------------------------------------------------------- Search ------
    def _apply_search_filter(self, text: str) -> None:
        text = text.strip().lower()
        selection_model = self._table.selectionModel()
        selection_model.clearSelection()

        if not text:
            self._table.viewport().update()
            return

        for row_index, order in enumerate(self._model.all_rows()):
            if text in (order.order_number or "").lower():
                index = self._model.index(row_index, 0)
                selection_model.select(index, selection_model.Select | selection_model.Rows)

    # ---------------------------------------------------- Context menu -----
    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Add", self._add_order)
        selection = self._current_selection()
        if selection.count:
            menu.addSeparator()
            menu.addAction("Edit", self._edit_selected)
            menu.addAction("Delete", self._delete_selected)
        menu.exec(self._table.viewport().mapToGlobal(position))

    # ------------------------------------------------------------ Actions ---
    def _add_order(self) -> None:
        with session_scope() as session:
            retailers = session.query(Retailer).order_by(Retailer.name).all()
            if not retailers:
                QMessageBox.information(self, "Add Order", "No retailers available.")
                return

            default_code = self._current_retailer_code()
            dialog = OrderDialog(
                session=session,
                retailers=retailers,
                parent=self,
                default_retailer_code=None if default_code == "ALL" else default_code,
            )

            if dialog.exec() != OrderDialog.Accepted:
                return

            result = dialog.result_data()
            if result is None:
                return

            order = Order(
                retailer_id=result.retailer.id,
                retailer=result.retailer,
                order_number=result.order_number,
                order_date=result.order_date,
                order_email=result.order_email,
                payment_method=result.payment_method,
                status=result.status,
                subtotal=result.items_subtotal,
                tax=Decimal("0.00"),
                shipping=Decimal("0.00"),
                total_cost=result.total_cost,
                credit_card_spend=result.credit_card_spend,
                gift_card_spend=Decimal("0.00"),
            )

            for item_entry in result.items:
                order.items.append(
                    OrderItem(
                        item_name=item_entry.item_name,
                        sku=item_entry.sku,
                        upc=item_entry.upc,
                        quantity=item_entry.quantity,
                        unit_price=item_entry.unit_price,
                        total_price=item_entry.total_price,
                    )
                )

            service = OrderService(session)

            try:
                service.create_order(order, allocations=result.allocations)
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to create order")
                QMessageBox.critical(self, "Add Order", f"Failed to create order:\n{exc}")
                return

        self.refresh()

    def _edit_selected(self) -> None:
        selection = self._current_selection()
        order = selection.ensure_single()
        if order is None:
            QMessageBox.information(self, "Edit Order", "Select one order to edit.")
            return

        with session_scope() as session:
            db_order = session.get(Order, order.id)
            if db_order is None:
                QMessageBox.warning(self, "Edit Order", "Selected order no longer exists.")
                return

            retailers = session.query(Retailer).order_by(Retailer.name).all()
            dialog = OrderDialog(session=session, retailers=retailers, parent=self, existing=db_order)

            if dialog.exec() != OrderDialog.Accepted:
                return

            result = dialog.result_data()
            if result is None:
                return

            db_order.order_number = result.order_number
            db_order.order_date = result.order_date
            db_order.order_email = result.order_email
            db_order.payment_method = result.payment_method
            db_order.status = result.status
            db_order.retailer = result.retailer
            db_order.subtotal = result.items_subtotal
            db_order.tax = Decimal("0.00")
            db_order.shipping = Decimal("0.00")
            db_order.total_cost = result.total_cost
            db_order.credit_card_spend = result.credit_card_spend

            db_order.items.clear()
            for item_entry in result.items:
                db_order.items.append(
                    OrderItem(
                        item_name=item_entry.item_name,
                        sku=item_entry.sku,
                        upc=item_entry.upc,
                        quantity=item_entry.quantity,
                        unit_price=item_entry.unit_price,
                        total_price=item_entry.total_price,
                    )
                )

            service = OrderService(session)

            try:
                service.update_gift_card_allocations(db_order, result.allocations)
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to update order")
                QMessageBox.critical(self, "Edit Order", f"Failed to update order:\n{exc}")
                return

        self.refresh()

    def _delete_selected(self) -> None:
        selection = self._current_selection()
        if selection.count == 0:
            QMessageBox.information(self, "Delete Orders", "No orders selected.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Orders",
            f"Delete {selection.count} selected order(s)? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        with session_scope() as session:
            service = OrderService(session)
            for order in selection.rows:
                db_order = session.get(Order, order.id)
                if db_order:
                    service.delete_order(db_order)
            try:
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to delete orders")
                QMessageBox.critical(self, "Delete Orders", f"Failed to delete orders:\n{exc}")
                return

        self.refresh()

    def _export_csv(self) -> None:
        QMessageBox.information(self, "Export", "Order export not implemented yet.")

    def _import_csv(self) -> None:
        QMessageBox.information(self, "Import", "Order import not implemented yet.")

    # --------------------------------------------------------- Helpers ------
    def _current_selection(self) -> OrderSelection:
        selection_model = self._table.selectionModel()
        selected_rows = selection_model.selectedRows()
        rows: List[Order] = []
        for index in selected_rows:
            rows.append(self._model.row_at(index.row()))
        return OrderSelection(rows)
