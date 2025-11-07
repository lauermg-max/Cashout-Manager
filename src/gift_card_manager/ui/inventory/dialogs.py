"""Dialogs for inventory management."""

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

from ...models import InventoryItem
from ...models.enums import InventorySourceType
from ...services import InventoryAdjustment


@dataclass
class InventoryItemDialogResult:
    item_name: str
    sku: str | None
    upc: str | None
    quantity_on_hand: int
    average_cost: Decimal
    total_cost: Decimal


class InventoryItemDialog(QDialog):
    """Dialog for creating or editing inventory items."""

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        existing: InventoryItem | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Edit Inventory Item" if existing else "Add Inventory Item")
        self._existing = existing
        self._result: InventoryItemDialogResult | None = None

        self._name_field = QLineEdit()
        self._sku_field = QLineEdit()
        self._upc_field = QLineEdit()
        self._quantity_field = self._int_field()
        self._avg_cost_field = self._currency_field()
        self._total_cost_field = self._currency_field()

        if existing:
            self._name_field.setText(existing.item_name)
            if existing.sku:
                self._sku_field.setText(existing.sku)
            if existing.upc:
                self._upc_field.setText(existing.upc)
            self._quantity_field.setValue(existing.quantity_on_hand or 0)
            self._avg_cost_field.setValue(float(existing.average_cost or Decimal("0")))
            self._total_cost_field.setValue(float(existing.total_cost or Decimal("0")))

        form = QFormLayout()
        form.addRow("Item Name", self._name_field)
        form.addRow("SKU", self._sku_field)
        form.addRow("UPC", self._upc_field)
        form.addRow("Quantity", self._quantity_field)
        form.addRow("Average Cost", self._avg_cost_field)
        form.addRow("Total Cost", self._total_cost_field)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form.addWidget(buttons)
        self.setLayout(form)
        self.setMinimumWidth(320)

    def result_data(self) -> InventoryItemDialogResult | None:
        return self._result

    def accept(self) -> None:
        name = self._name_field.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Item name is required.")
            return

        quantity = self._quantity_field.value()
        average_cost = Decimal(str(self._avg_cost_field.value())).quantize(Decimal("0.01"))
        total_cost = Decimal(str(self._total_cost_field.value())).quantize(Decimal("0.01"))

        self._result = InventoryItemDialogResult(
            item_name=name,
            sku=self._sku_field.text().strip() or None,
            upc=self._upc_field.text().strip() or None,
            quantity_on_hand=quantity,
            average_cost=average_cost,
            total_cost=total_cost,
        )
        super().accept()

    @staticmethod
    def _currency_field() -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setDecimals(2)
        box.setMaximum(1_000_000)
        box.setMinimum(0.0)
        box.setSingleStep(1.0)
        return box

    @staticmethod
    def _int_field() -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setDecimals(0)
        box.setMaximum(1_000_000)
        box.setMinimum(0)
        box.setSingleStep(1)
        return box


@dataclass
class InventoryAdjustmentDialogResult:
    adjustment: InventoryAdjustment


class InventoryAdjustmentDialog(QDialog):
    """Dialog for creating inventory adjustments."""

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Inventory Adjustment")
        self._result: InventoryAdjustmentDialogResult | None = None

        self._source_combo = QComboBox()
        for source in InventorySourceType:
            self._source_combo.addItem(source.value.title(), source)

        self._quantity_field = QDoubleSpinBox()
        self._quantity_field.setDecimals(0)
        self._quantity_field.setMinimum(-1_000_000)
        self._quantity_field.setMaximum(1_000_000)
        self._quantity_field.setValue(0)
        self._quantity_field.setSingleStep(1)

        self._cost_field = QDoubleSpinBox()
        self._cost_field.setDecimals(2)
        self._cost_field.setMinimum(-1_000_000)
        self._cost_field.setMaximum(1_000_000)
        self._cost_field.setValue(0.0)
        self._cost_field.setSingleStep(1.0)

        self._notes_field = QLineEdit()

        form = QFormLayout()
        form.addRow("Source", self._source_combo)
        form.addRow("Quantity Change", self._quantity_field)
        form.addRow("Cost Change", self._cost_field)
        form.addRow("Notes", self._notes_field)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form.addWidget(buttons)
        self.setLayout(form)
        self.setMinimumWidth(320)

    def result_data(self) -> InventoryAdjustmentDialogResult | None:
        return self._result

    def accept(self) -> None:
        quantity = int(self._quantity_field.value())
        cost_change = Decimal(str(self._cost_field.value())).quantize(Decimal("0.01"))

        if quantity == 0 and cost_change == Decimal("0"):
            QMessageBox.warning(self, "Validation", "Enter a quantity or cost change.")
            return

        source_type = self._source_combo.currentData(Qt.ItemDataRole.UserRole)
        notes = self._notes_field.text().strip() or None

        adjustment = InventoryAdjustment(
            quantity_change=quantity,
            cost_change=cost_change,
            source_type=source_type,
            notes=notes,
        )
        self._result = InventoryAdjustmentDialogResult(adjustment=adjustment)
        super().accept()
