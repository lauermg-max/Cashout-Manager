"""Dialogs for creating and editing gift cards."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from ...models import GiftCard, Retailer


@dataclass
class GiftCardDialogResult:
    retailer: Retailer
    card_number: str
    pin: str | None
    acquisition_cost: Decimal
    face_value: Decimal
    remaining_balance: Decimal


class GiftCardDialog(QDialog):
    """Dialog used to create or edit a gift card."""

    def __init__(
        self,
        retailers: Sequence[Retailer],
        *,
        parent: QWidget | None = None,
        existing: GiftCard | None = None,
        default_retailer_code: str | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Edit Gift Card" if existing else "Add Gift Card")
        self._retailers = list(retailers)
        self._existing = existing
        self._result: GiftCardDialogResult | None = None

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

        self._card_number_field = QLineEdit()
        self._pin_field = QLineEdit()
        self._pin_field.setEchoMode(QLineEdit.Normal)

        self._acquisition_field = self._currency_field()
        self._face_field = self._currency_field()
        self._remaining_field = self._currency_field()

        if existing:
            self._card_number_field.setText(existing.card_number)
            if existing.card_pin:
                self._pin_field.setText(existing.card_pin)
            if existing.acquisition_cost is not None:
                self._acquisition_field.setValue(float(existing.acquisition_cost))
            if existing.face_value is not None:
                self._face_field.setValue(float(existing.face_value))
            if existing.remaining_balance is not None:
                self._remaining_field.setValue(float(existing.remaining_balance))

        form = QFormLayout()
        form.addRow("Retailer", self._retailer_combo)
        form.addRow("Card Number", self._card_number_field)
        form.addRow("Pin", self._pin_field)
        form.addRow("Acquisition Cost", self._acquisition_field)
        form.addRow("Face Value", self._face_field)
        form.addRow("Remaining Balance", self._remaining_field)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form.addRow(buttons)
        self.setLayout(form)
        self.setMinimumWidth(320)

    def result_data(self) -> GiftCardDialogResult | None:
        return self._result

    def accept(self) -> None:
        retailer = self._retailer_combo.currentData(Qt.ItemDataRole.UserRole)
        if retailer is None:
            QMessageBox.warning(self, "Validation", "Select a retailer.")
            return

        card_number = self._card_number_field.text().strip()
        if not card_number:
            QMessageBox.warning(self, "Validation", "Card number is required.")
            return

        pin = self._pin_field.text().strip() or None
        if retailer.requires_pin and not pin:
            QMessageBox.warning(self, "Validation", "This retailer requires a PIN.")
            return

        acquisition = Decimal(str(self._acquisition_field.value())).quantize(Decimal("0.01"))
        face_value = Decimal(str(self._face_field.value())).quantize(Decimal("0.01"))
        remaining_raw = Decimal(str(self._remaining_field.value())).quantize(Decimal("0.01"))
        remaining_balance = remaining_raw if remaining_raw != Decimal("0.00") else face_value

        self._result = GiftCardDialogResult(
            retailer=retailer,
            card_number=card_number,
            pin=pin,
            acquisition_cost=acquisition,
            face_value=face_value,
            remaining_balance=remaining_balance,
        )
        super().accept()

    @staticmethod
    def _currency_field() -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setDecimals(2)
        box.setMaximum(1_000_000)
        box.setMinimum(0)
        box.setSingleStep(1.0)
        box.setValue(0.0)
        return box
