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
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...models import GiftCard, Order, Retailer
from ...models.enums import OrderStatus, PaymentMethod
from ...services import GiftCardAllocation


@dataclass
class OrderDialogResult:
    retailer: Retailer
    order_number: str
    order_date: date
    order_email: str | None
    payment_method: PaymentMethod
    status: OrderStatus
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total_cost: Decimal
    credit_card_spend: Decimal
    allocations: List[GiftCardAllocation]


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
        self._result: OrderDialogResult | None = None

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

        currency_fields = []
        self._subtotal_field = self._currency_field()
        currency_fields.append(self._subtotal_field)
        self._tax_field = self._currency_field()
        currency_fields.append(self._tax_field)
        self._shipping_field = self._currency_field()
        currency_fields.append(self._shipping_field)
        self._total_field = self._currency_field()
        currency_fields.append(self._total_field)
        self._credit_field = self._currency_field()
        currency_fields.append(self._credit_field)

        # Gift card allocation controls
        self._allocation_combo = QComboBox()
        self._allocation_amount = self._currency_field()
        self._allocation_amount.setMaximum(1_000_000)
        self._allocation_amount.setMinimum(0.01)
        self._allocation_amount.setSingleStep(1.0)

        add_allocation_button = QPushButton("Add Allocation")
        add_allocation_button.clicked.connect(self._add_allocation)

        remove_allocation_button = QPushButton("Remove Selected")
        remove_allocation_button.clicked.connect(self._remove_selected_allocation)

        self._allocation_list = QListWidget()

        self._retailer_combo.currentIndexChanged.connect(self._load_gift_cards_for_retailer)

        # Populate for editing
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
            if existing.subtotal is not None:
                self._subtotal_field.setValue(float(existing.subtotal))
            if existing.tax is not None:
                self._tax_field.setValue(float(existing.tax))
            if existing.shipping is not None:
                self._shipping_field.setValue(float(existing.shipping))
            if existing.total_cost is not None:
                self._total_field.setValue(float(existing.total_cost))
            if existing.credit_card_spend is not None:
                self._credit_field.setValue(float(existing.credit_card_spend))

        # Layout ----------------------------------------------------------------
        form = QFormLayout()
        form.addRow("Retailer", self._retailer_combo)
        form.addRow("Order Number", self._order_number_field)
        form.addRow("Order Date", self._date_field)
        form.addRow("Email", self._email_field)
        form.addRow("Payment Method", self._payment_combo)
        form.addRow("Status", self._status_combo)
        form.addRow("Subtotal", self._subtotal_field)
        form.addRow("Tax", self._tax_field)
        form.addRow("Shipping", self._shipping_field)
        form.addRow("Total Cost", self._total_field)
        form.addRow("Credit Card Spend", self._credit_field)

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
        layout.addLayout(allocation_row)
        layout.addWidget(self._allocation_list)
        layout.addLayout(allocation_buttons)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setMinimumWidth(420)

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

        order_date = self._date_field.date().toPython()
        email = self._email_field.text().strip() or None

        payment_method = self._payment_combo.currentData(Qt.ItemDataRole.UserRole)
        status = self._status_combo.currentData(Qt.ItemDataRole.UserRole)

        subtotal = self._decimal_from_spin(self._subtotal_field)
        tax = self._decimal_from_spin(self._tax_field)
        shipping = self._decimal_from_spin(self._shipping_field)
        total_cost = self._decimal_from_spin(self._total_field)
        credit = self._decimal_from_spin(self._credit_field)

        if total_cost <= 0:
            QMessageBox.warning(self, "Validation", "Total cost must be greater than zero.")
            return

        self._result = OrderDialogResult(
            retailer=retailer,
            order_number=order_number,
            order_date=order_date,
            order_email=email,
            payment_method=payment_method,
            status=status,
            subtotal=subtotal,
            tax=tax,
            shipping=shipping,
            total_cost=total_cost,
            credit_card_spend=credit,
            allocations=list(self._allocations),
        )

        super().accept()

    @staticmethod
    def _decimal_from_spin(spin: QDoubleSpinBox) -> Decimal:
        return Decimal(str(spin.value())).quantize(Decimal("0.01"))
