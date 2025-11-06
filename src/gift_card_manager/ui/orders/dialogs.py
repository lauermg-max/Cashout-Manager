"""Dialogs for creating and editing orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Sequence

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import GiftCard, Order, Retailer
from ...models.enums import OrderStatus, PaymentMethod
from ...services import GiftCardAllocation


@dataclass
class OrderItemEntry:
    item_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    sku: str | None = None
    upc: str | None = None


@dataclass
class OrderDialogResult:
    retailer: Retailer
    order_number: str
    order_date: date
    order_email: str | None
    payment_method: PaymentMethod
    status: OrderStatus
    items: List[OrderItemEntry]
    items_subtotal: Decimal
    total_cost: Decimal
    credit_card_spend: Decimal
    allocations: List[GiftCardAllocation]


class OrderItemDialog(QDialog):
    """Dialog used to add or edit a single order line item."""

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        existing: OrderItemEntry | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Edit Item" if existing else "Add Item")
        self._data: OrderItemEntry | None = None

        self._item_field = QLineEdit()
        self._sku_field = QLineEdit()
        self._upc_field = QLineEdit()
        self._quantity_field = QSpinBox()
        self._quantity_field.setMinimum(1)
        self._quantity_field.setMaximum(1_000_000)
        self._unit_price_field = QDoubleSpinBox()
        self._unit_price_field.setDecimals(2)
        self._unit_price_field.setMaximum(1_000_000)
        self._unit_price_field.setMinimum(0.0)
        self._unit_price_field.setSingleStep(1.0)

        if existing:
            self._item_field.setText(existing.item_name)
            if existing.sku:
                self._sku_field.setText(existing.sku)
            if existing.upc:
                self._upc_field.setText(existing.upc)
            self._quantity_field.setValue(existing.quantity)
            self._unit_price_field.setValue(float(existing.unit_price))

        form = QFormLayout()
        form.addRow("Name", self._item_field)
        form.addRow("SKU", self._sku_field)
        form.addRow("UPC", self._upc_field)
        form.addRow("Quantity", self._quantity_field)
        form.addRow("Unit Price", self._unit_price_field)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @property
    def data(self) -> OrderItemEntry | None:
        return self._data

    def accept(self) -> None:
        name = self._item_field.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Item name is required.")
            return

        quantity = self._quantity_field.value()
        if quantity <= 0:
            QMessageBox.warning(self, "Validation", "Quantity must be at least 1.")
            return

        unit_price = Decimal(str(self._unit_price_field.value())).quantize(Decimal("0.01"))
        total_price = (unit_price * Decimal(quantity)).quantize(Decimal("0.01"))

        sku = self._sku_field.text().strip() or None
        upc = self._upc_field.text().strip() or None

        self._data = OrderItemEntry(
            item_name=name,
            sku=sku,
            upc=upc,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
        )

        super().accept()


class OrderDialog(QDialog):
    """Dialog for creating or editing orders."""

    def __init__(
        self,
        *,
        session,
        retailers: Sequence[Retailer],
        parent: QWidget | None = None,
        existing: Order | None = None,
        default_retailer_code: str | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Edit Order" if existing else "Add Order")
        self._session = session
        self._retailers = list(retailers)
        self._existing = existing
        self._allocations: List[GiftCardAllocation] = []
        self._item_entries: List[OrderItemEntry] = []
        self._result: OrderDialogResult | None = None
        self._user_adjusted_total = False
        self._setting_total_field = False

        # ---------------------------------------------------------------- UI
        self._retailer_combo = QComboBox()
        for retailer in self._retailers:
            text = f"{retailer.name} ({retailer.code})"
            idx = self._retailer_combo.count()
            self._retailer_combo.addItem(text, retailer)
            if existing and retailer.id == existing.retailer_id:
                self._retailer_combo.setCurrentIndex(idx)

        if existing:
            self._retailer_combo.setEnabled(False)
        elif default_retailer_code:
            default_code = default_retailer_code.upper()
            for idx in range(self._retailer_combo.count()):
                retailer: Retailer = self._retailer_combo.itemData(idx)
                if retailer and retailer.code == default_code:
                    self._retailer_combo.setCurrentIndex(idx)
                    break

        self._order_number_field = QLineEdit()
        self._date_field = QDateEdit()
        self._date_field.setCalendarPopup(True)
        self._date_field.setDate(QDate.currentDate())

        self._email_field = QLineEdit()

        self._payment_combo = QComboBox()
        for method in PaymentMethod:
            self._payment_combo.addItem(method.value.replace("_", " ").title(), method)

        self._status_combo = QComboBox()
        for status in OrderStatus:
            self._status_combo.addItem(status.value.title(), status)

        self._total_field = self._currency_field()
        self._total_field.valueChanged.connect(self._on_total_field_changed)

        # Gift card allocation controls
        self._allocation_combo = QComboBox()
        self._allocation_amount = self._currency_field()
        self._allocation_amount.setMaximum(1_000_000)
        self._allocation_amount.setMinimum(0.0)
        self._allocation_amount.setSingleStep(1.0)

        add_allocation_button = QPushButton("Add Allocation")
        add_allocation_button.clicked.connect(self._add_allocation)

        remove_allocation_button = QPushButton("Remove Selected")
        remove_allocation_button.clicked.connect(self._remove_selected_allocation)

        self._allocation_list = QListWidget()

        self._retailer_combo.currentIndexChanged.connect(self._load_gift_cards_for_retailer)

        # Order items table
        self._items_table = QTableWidget(0, 6)
        self._items_table.setHorizontalHeaderLabels(
            ["Item", "SKU", "UPC", "Qty", "Unit Price", "Line Total"]
        )
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._items_table.setSelectionMode(QTableWidget.SingleSelection)
        self._items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        header: QHeaderView = self._items_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

        item_buttons = QHBoxLayout()
        add_item_button = QPushButton("Add Item")
        add_item_button.clicked.connect(self._add_item)
        edit_item_button = QPushButton("Edit Item")
        edit_item_button.clicked.connect(self._edit_item)
        remove_item_button = QPushButton("Remove Item")
        remove_item_button.clicked.connect(self._remove_item)
        item_buttons.addWidget(add_item_button)
        item_buttons.addWidget(edit_item_button)
        item_buttons.addWidget(remove_item_button)
        item_buttons.addStretch(1)

        self._items_total_label = QLabel("Items total: $0.00")
        self._payment_summary_label = QLabel("Gift Cards: $0.00 | Credit Card: $0.00")

        # Layout ----------------------------------------------------------------
        form = QFormLayout()
        form.addRow("Retailer", self._retailer_combo)
        form.addRow("Order Number", self._order_number_field)
        form.addRow("Order Date", self._date_field)
        form.addRow("Email", self._email_field)
        form.addRow("Payment Method", self._payment_combo)
        form.addRow("Status", self._status_combo)
        form.addRow("Total Cost", self._total_field)

        allocation_row = QHBoxLayout()
        allocation_row.addWidget(QLabel("Gift Card"))
        allocation_row.addWidget(self._allocation_combo, 1)
        allocation_row.addWidget(QLabel("Amount"))
        allocation_row.addWidget(self._allocation_amount)
        allocation_row.addWidget(add_allocation_button)

        allocation_buttons = QHBoxLayout()
        allocation_buttons.addWidget(remove_allocation_button)
        allocation_buttons.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._items_table)
        layout.addLayout(item_buttons)
        layout.addWidget(self._items_total_label)
        layout.addWidget(self._payment_summary_label)
        layout.addSpacing(8)
        layout.addLayout(allocation_row)
        layout.addWidget(self._allocation_list)
        layout.addLayout(allocation_buttons)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setMinimumWidth(520)

        # Populate for editing ------------------------------------------------
        if existing:
            self._order_number_field.setText(existing.order_number or "")
            if existing.order_date:
                self._date_field.setDate(QDate(existing.order_date.year, existing.order_date.month, existing.order_date.day))
            if existing.order_email:
                self._email_field.setText(existing.order_email)
            if existing.payment_method:
                self._set_combo_by_value(self._payment_combo, existing.payment_method)
            if existing.status:
                self._set_combo_by_value(self._status_combo, existing.status)

            for item in existing.items:
                entry = OrderItemEntry(
                    item_name=item.item_name,
                    sku=item.sku,
                    upc=item.upc,
                    quantity=item.quantity,
                    unit_price=Decimal(str(item.unit_price or 0)).quantize(Decimal("0.01")),
                    total_price=Decimal(str(item.total_price or 0)).quantize(Decimal("0.01")),
                )
                self._item_entries.append(entry)

            if existing.total_cost is not None:
                self._set_total_field(Decimal(str(existing.total_cost)))
                self._user_adjusted_total = True

        self._load_gift_cards_for_retailer()

        if existing:
            for usage in existing.gift_cards_used:
                card = usage.gift_card
                if card is None:
                    card = self._session.get(GiftCard, usage.gift_card_id)
                if card is None:
                    continue
                allocation = GiftCardAllocation(
                    gift_card_id=card.id,
                    amount=Decimal(usage.amount_used).quantize(Decimal("0.01")),
                )
                self._allocations.append(allocation)
        self._refresh_allocation_list()
        self._refresh_items_table()

    # ---------------------------------------------------------------- Helpers
    def result_data(self) -> OrderDialogResult | None:
        return self._result

    def _currency_field(self) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setDecimals(2)
        box.setMaximum(1_000_000)
        box.setMinimum(0.0)
        box.setSingleStep(1.0)
        return box

    def _set_combo_by_value(self, combo: QComboBox, value) -> None:
        for idx in range(combo.count()):
            if combo.itemData(idx) == value:
                combo.setCurrentIndex(idx)
                break

    def _load_gift_cards_for_retailer(self) -> None:
        self._allocation_combo.blockSignals(True)
        self._allocation_combo.clear()

        retailer = self._retailer_combo.currentData(Qt.ItemDataRole.UserRole)
        if retailer is None:
            self._allocation_combo.blockSignals(False)
            return

        cards = (
            self._session.query(GiftCard)
            .filter(GiftCard.retailer_id == retailer.id)
            .order_by(GiftCard.sku)
            .all()
        )

        for card in cards:
            remaining = card.remaining_balance or Decimal("0")
            text = f"{card.sku} ({remaining:.2f})"
            self._allocation_combo.addItem(text, card)

        self._allocation_combo.blockSignals(False)

    def _add_item(self) -> None:
        dialog = OrderItemDialog(parent=self)
        if dialog.exec() != OrderItemDialog.Accepted or dialog.data is None:
            return
        self._item_entries.append(dialog.data)
        self._refresh_items_table()

    def _edit_item(self) -> None:
        row = self._items_table.currentRow()
        if row < 0 or row >= len(self._item_entries):
            return
        existing = self._item_entries[row]
        dialog = OrderItemDialog(parent=self, existing=existing)
        if dialog.exec() != OrderItemDialog.Accepted or dialog.data is None:
            return
        self._item_entries[row] = dialog.data
        self._refresh_items_table()

    def _remove_item(self) -> None:
        row = self._items_table.currentRow()
        if row < 0 or row >= len(self._item_entries):
            return
        self._item_entries.pop(row)
        self._refresh_items_table()

    def _refresh_items_table(self) -> None:
        self._items_table.setRowCount(len(self._item_entries))
        for row, entry in enumerate(self._item_entries):
            values = [
                entry.item_name,
                entry.sku or "",
                entry.upc or "",
                str(entry.quantity),
                f"${entry.unit_price:.2f}",
                f"${entry.total_price:.2f}",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column >= 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._items_table.setItem(row, column, item)

        self._update_totals_from_items()

    def _items_subtotal(self) -> Decimal:
        total = Decimal("0")
        for entry in self._item_entries:
            total += entry.total_price
        return total.quantize(Decimal("0.01"))

    def _update_totals_from_items(self) -> None:
        subtotal = self._items_subtotal()
        self._items_total_label.setText(f"Items total: ${subtotal:.2f}")
        if not self._user_adjusted_total:
            self._set_total_field(subtotal)
        self._update_payment_summary()

    def _set_total_field(self, value: Decimal) -> None:
        self._setting_total_field = True
        self._total_field.setValue(float(value))
        self._setting_total_field = False

    def _on_total_field_changed(self, _value: float) -> None:
        if not self._setting_total_field:
            self._user_adjusted_total = True
        self._update_payment_summary()

    def _add_allocation(self) -> None:
        card: GiftCard | None = self._allocation_combo.currentData(Qt.ItemDataRole.UserRole)
        if card is None:
            QMessageBox.warning(self, "Allocation", "Select a gift card.")
            return

        amount = Decimal(str(self._allocation_amount.value())).quantize(Decimal("0.01"))
        if amount <= 0:
            QMessageBox.warning(self, "Allocation", "Amount must be positive.")
            return

        allocation = GiftCardAllocation(gift_card_id=card.id, amount=amount)
        self._allocations.append(allocation)
        self._refresh_allocation_list()

    def _remove_selected_allocation(self) -> None:
        selected = self._allocation_list.currentRow()
        if selected < 0:
            return
        self._allocations.pop(selected)
        self._refresh_allocation_list()

    def _refresh_allocation_list(self) -> None:
        self._allocation_list.clear()
        for allocation in self._allocations:
            card = self._session.get(GiftCard, allocation.gift_card_id)
            sku = card.sku if card else str(allocation.gift_card_id)
            item = QListWidgetItem(f"{sku}: ${allocation.amount:.2f}")
            self._allocation_list.addItem(item)
        self._update_payment_summary()

    def _gift_card_total(self) -> Decimal:
        total = Decimal("0")
        for allocation in self._allocations:
            total += allocation.amount
        return total.quantize(Decimal("0.01"))

    def _current_total_cost(self) -> Decimal:
        return Decimal(str(self._total_field.value())).quantize(Decimal("0.01"))

    def _update_payment_summary(self) -> None:
        gift_total = self._gift_card_total()
        total_cost = self._current_total_cost()
        credit = (total_cost - gift_total).quantize(Decimal("0.01"))
        self._payment_summary_label.setText(
            f"Gift Cards: ${gift_total:.2f} | Credit Card: ${credit:.2f}"
        )

    # ---------------------------------------------------------------- Accept
    def accept(self) -> None:
        retailer = self._retailer_combo.currentData(Qt.ItemDataRole.UserRole)
        if retailer is None:
            QMessageBox.warning(self, "Validation", "Select a retailer.")
            return

        order_number = self._order_number_field.text().strip()
        if not order_number:
            QMessageBox.warning(self, "Validation", "Order number is required.")
            return

        if not self._item_entries:
            QMessageBox.warning(self, "Validation", "Add at least one item to the order.")
            return

        order_date = self._date_field.date().toPython()
        email = self._email_field.text().strip() or None

        payment_method = self._payment_combo.currentData(Qt.ItemDataRole.UserRole)
        status = self._status_combo.currentData(Qt.ItemDataRole.UserRole)

        total_cost = self._current_total_cost()
        if total_cost <= 0:
            QMessageBox.warning(self, "Validation", "Total cost must be greater than zero.")
            return

        gift_total = self._gift_card_total()
        if gift_total > total_cost:
            QMessageBox.warning(
                self,
                "Validation",
                "Gift card allocations cannot exceed the total order cost.",
            )
            return

        credit = (total_cost - gift_total).quantize(Decimal("0.01"))

        items_subtotal = self._items_subtotal()

        self._result = OrderDialogResult(
            retailer=retailer,
            order_number=order_number,
            order_date=order_date,
            order_email=email,
            payment_method=payment_method,
            status=status,
            items=list(self._item_entries),
            items_subtotal=items_subtotal,
            total_cost=total_cost,
            credit_card_spend=credit,
            allocations=list(self._allocations),
        )

        super().accept()
