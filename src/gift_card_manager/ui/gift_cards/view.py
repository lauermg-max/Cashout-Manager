"""Gift card inventory view widget."""

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

from ...core import session_scope
from ...io import export_gift_cards_to_csv, import_gift_cards_from_csv
from ...models import GiftCard, Retailer
from ...services import GiftCardService
from .dialogs import GiftCardDialog
from .model import GiftCardTableModel

logger = logging.getLogger(__name__)


@dataclass
class GiftCardSelection:
    rows: List[GiftCard]

    @property
    def count(self) -> int:
        return len(self.rows)

    def ensure_single(self) -> GiftCard | None:
        if self.count != 1:
            return None
        return self.rows[0]


class GiftCardInventoryView(QWidget):
    """Composite widget showing gift cards and actions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = GiftCardTableModel()
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
        self._search_field.setPlaceholderText("Search by SKU or card number…")
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
        toolbar = QToolBar("Gift Card Actions", self)
        toolbar.setMovable(False)

        add_action = toolbar.addAction("Add")
        add_action.triggered.connect(self._add_gift_card)

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
            cards = self._load_gift_cards(session)
        self._model.set_rows(cards)
        self._apply_search_filter(self._search_field.text())

    def _load_gift_cards(self, session) -> Iterable[GiftCard]:
        service = GiftCardService(session)
        retailer_code = self._current_retailer_code()
        if retailer_code == "ALL":
            return service.list_gift_cards()
        retailer = (
            session.query(Retailer)
            .filter(Retailer.code == retailer_code)
            .one_or_none()
        )
        if retailer is None:
            return []
        return (
            session.query(GiftCard)
            .filter(GiftCard.retailer_id == retailer.id)
            .order_by(GiftCard.sku)
            .all()
        )

    def _load_retailers(self) -> None:
        self._retailer_filter.blockSignals(True)
        self._retailer_filter.clear()
        self._retailer_filter.addItem("All Retailers", "ALL")
        with session_scope() as session:
            retailers = session.query(Retailer).order_by(Retailer.name).all()
        for retailer in retailers:
            display = f"{retailer.name} ({retailer.code})"
            self._retailer_filter.addItem(display, retailer.code)
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

        for row_index, card in enumerate(self._model.all_rows()):
            if text in card.sku.lower() or text in card.card_number.lower():
                index = self._model.index(row_index, 0)
                selection_model.select(index, selection_model.Select | selection_model.Rows)

    # ---------------------------------------------------- Context menu -----
    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Add", self._add_gift_card)
        selection = self._current_selection()
        if selection.count:
            menu.addSeparator()
            menu.addAction("Edit", self._edit_selected)
            menu.addAction("Delete", self._delete_selected)
        menu.exec(self._table.viewport().mapToGlobal(position))

    # ------------------------------------------------------------ Actions ---
    def _add_gift_card(self) -> None:
        with session_scope() as session:
            retailers = session.query(Retailer).order_by(Retailer.name).all()
            if not retailers:
                QMessageBox.information(self, "Add Gift Card", "No retailers available.")
                return

            default_code = self._current_retailer_code()
            dialog = GiftCardDialog(
                retailers, parent=self, default_retailer_code=None if default_code == "ALL" else default_code
            )

            if dialog.exec() != GiftCardDialog.Accepted:
                return

            result = dialog.result_data()
            if result is None:
                return

            service = GiftCardService(session)
            new_card = GiftCard(
                retailer_id=result.retailer.id,
                card_number=result.card_number,
                card_pin=result.pin,
                acquisition_cost=result.acquisition_cost,
                face_value=result.face_value,
                remaining_balance=result.remaining_balance,
            )
            new_card.retailer = result.retailer
            try:
                service.create_gift_card(new_card)
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to create gift card")
                QMessageBox.critical(self, "Error", f"Failed to save gift card:\n{exc}")
                return

        self.refresh()

    def _edit_selected(self) -> None:
        selection = self._current_selection()
        card = selection.ensure_single()
        if card is None:
            QMessageBox.information(self, "Edit Gift Card", "Select one gift card to edit.")
            return
        with session_scope() as session:
            db_card = session.get(GiftCard, card.id)
            if db_card is None:
                QMessageBox.warning(self, "Edit Gift Card", "Selected gift card no longer exists.")
                return

            retailers = session.query(Retailer).order_by(Retailer.name).all()
            dialog = GiftCardDialog(retailers, parent=self, existing=db_card)

            if dialog.exec() != GiftCardDialog.Accepted:
                return

            result = dialog.result_data()
            if result is None:
                return

            db_card.card_number = result.card_number
            db_card.card_pin = result.pin
            db_card.acquisition_cost = result.acquisition_cost
            db_card.face_value = result.face_value
            db_card.remaining_balance = result.remaining_balance

            try:
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to update gift card")
                QMessageBox.critical(self, "Error", f"Failed to update gift card:\n{exc}")
                return

        self.refresh()

    def _delete_selected(self) -> None:
        selection = self._current_selection()
        if selection.count == 0:
            QMessageBox.information(self, "Delete Gift Cards", "No gift cards selected.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Gift Cards",
            f"Delete {selection.count} selected gift card(s)? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        with session_scope() as session:
            for card in selection.rows:
                db_card = session.get(GiftCard, card.id)
                if db_card:
                    session.delete(db_card)
            session.commit()

        self.refresh()

    def _export_csv(self) -> None:
        retailer_code = self._current_retailer_code()
        if retailer_code == "ALL":
            QMessageBox.information(self, "Export", "Select a specific retailer first.")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export Gift Cards",
            "gift_cards.csv",
            "CSV Files (*.csv)",
        )
        if not file_name:
            return

        path = Path(file_name)
        with session_scope() as session:
            try:
                export_gift_cards_to_csv(path, retailer_code, session)
            except Exception as exc:  # pragma: no cover - UI feedback
                logger.exception("Failed to export gift cards")
                QMessageBox.critical(self, "Export", f"Failed to export CSV:\n{exc}")
                return

        QMessageBox.information(self, "Export", f"Exported gift cards to {path}.")

    def _import_csv(self) -> None:
        retailer_code = self._current_retailer_code()
        if retailer_code == "ALL":
            QMessageBox.information(self, "Import", "Select a specific retailer first.")
            return

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Import Gift Cards",
            "",
            "CSV Files (*.csv)",
        )
        if not file_name:
            return

        path = Path(file_name)
        with session_scope() as session:
            try:
                rows = import_gift_cards_from_csv(path, retailer_code, session)
            except Exception as exc:  # pragma: no cover - UI feedback
                logger.exception("Failed to import gift cards")
                QMessageBox.critical(self, "Import", f"Failed to parse CSV:\n{exc}")
                return

            if not rows:
                QMessageBox.information(self, "Import", "No gift cards found in CSV.")
                return

            service = GiftCardService(session)
            created = 0
            for row in rows:
                retailer = (
                    session.query(Retailer)
                    .filter(Retailer.code == row.retailer_code)
                    .one_or_none()
                )
                if retailer is None:
                    logger.warning("Skipping row for unknown retailer %s", row.retailer_code)
                    continue

                new_card = GiftCard(
                    retailer_id=retailer.id,
                    card_number=row.card_number,
                    card_pin=row.pin,
                    acquisition_cost=row.acquisition_cost or Decimal("0"),
                    face_value=row.face_value or Decimal("0"),
                    remaining_balance=row.remaining_balance
                    if row.remaining_balance is not None
                    else (row.face_value or Decimal("0")),
                )
                new_card.retailer = retailer
                try:
                    service.create_gift_card(new_card)
                    created += 1
                except Exception as exc:  # pragma: no cover - UI feedback
                    logger.warning("Skipping gift card due to error: %s", exc)
            try:
                session.commit()
            except Exception as exc:  # pragma: no cover - UI feedback
                session.rollback()
                logger.exception("Failed to import gift cards")
                QMessageBox.critical(self, "Import", f"Failed to import gift cards:\n{exc}")
                return

        QMessageBox.information(self, "Import", f"Imported {created} gift card(s).")
        self.refresh()

    # --------------------------------------------------------- Helpers ------
    def _current_selection(self) -> GiftCardSelection:
        selection_model = self._table.selectionModel()
        selected_rows = selection_model.selectedRows()
        rows: List[GiftCard] = []
        for index in selected_rows:
            rows.append(self._model.row_at(index.row()))
        return GiftCardSelection(rows)
