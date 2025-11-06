"""Table model for displaying orders."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from ...models import Order


class OrdersTableModel(QAbstractTableModel):
    """Qt model for order listings."""

    HEADERS = [
        "Order #",
        "Retailer",
        "Date",
        "Total",
        "Gift Card",
        "Status",
    ]

    def __init__(self, rows: Sequence[Order] | None = None) -> None:
        super().__init__()
        self._rows: List[Order] = list(rows or [])

    # ----------------------------------------------------------------- Qt API
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

        order = self._rows[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            return self._display_value(order, column)

        if role == Qt.TextAlignmentRole and column in (3, 4):
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

    # ---------------------------------------------------------------- Helpers
    def set_rows(self, rows: Sequence[Order]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, row_index: int) -> Order:
        return self._rows[row_index]

    def all_rows(self) -> List[Order]:
        return list(self._rows)

    def _display_value(self, order: Order, column: int):
        if column == 0:
            return order.order_number
        if column == 1:
            return order.retailer.name if order.retailer else ""
        if column == 2:
            return self._format_date(order.order_date)
        if column == 3:
            return self._format_currency(order.total_cost)
        if column == 4:
            return self._format_currency(order.gift_card_spend)
        if column == 5:
            status = order.status.value if hasattr(order.status, "value") else str(order.status or "")
            return status.title()
        return ""

    @staticmethod
    def _format_date(value: date | None) -> str:
        if not value:
            return ""
        return value.strftime("%Y-%m-%d")

    @staticmethod
    def _format_currency(value: Decimal | float | int | None) -> str:
        if value is None:
            return ""
        if isinstance(value, Decimal):
            return f"${value:.2f}"
        return f"${Decimal(value):.2f}"
