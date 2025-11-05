"""Inventory table model."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from ...models import InventoryItem


class InventoryTableModel(QAbstractTableModel):
    """Qt model representing inventory items."""

    HEADERS = [
        "Item",
        "SKU",
        "UPC",
        "Quantity",
        "Avg Cost",
        "Total Cost",
    ]

    def __init__(self, rows: Sequence[InventoryItem] | None = None) -> None:
        super().__init__()
        self._rows: List[InventoryItem] = list(rows or [])

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent and parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent and parent.isValid():
            return 0
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None

        item = self._rows[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            return self._display_value(item, column)

        if role == Qt.TextAlignmentRole and column in (3, 4, 5):
            return Qt.AlignRight | Qt.AlignVCenter

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def set_rows(self, rows: Sequence[InventoryItem]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, row_index: int) -> InventoryItem:
        return self._rows[row_index]

    def all_rows(self) -> List[InventoryItem]:
        return list(self._rows)

    def _display_value(self, item: InventoryItem, column: int):
        if column == 0:
            return item.item_name
        if column == 1:
            return item.sku or ""
        if column == 2:
            return item.upc or ""
        if column == 3:
            return str(item.quantity_on_hand or 0)
        if column == 4:
            return self._format_currency(item.average_cost)
        if column == 5:
            return self._format_currency(item.total_cost)
        return ""

    @staticmethod
    def _format_currency(value: Decimal | float | int | None) -> str:
        if value is None:
            return ""
        if isinstance(value, Decimal):
            return f"${value:.2f}"
        return f"${Decimal(value):.2f}"
