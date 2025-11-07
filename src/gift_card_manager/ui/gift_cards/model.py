"""Model for displaying gift cards in a Qt view."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from ...models import GiftCard


class GiftCardTableModel(QAbstractTableModel):
    """Qt model representing a collection of gift cards."""

    HEADERS = [
        "SKU",
        "Card Number",
        "Pin",
        "Retailer",
        "Cost",
        "Value",
        "Remaining",
    ]

    def __init__(self, rows: Sequence[GiftCard] | None = None) -> None:
        super().__init__()
        self._rows: List[GiftCard] = list(rows or [])

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

        card = self._rows[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            return self._display_value(card, column)

        if role == Qt.ToolTipRole:
            return self._tooltip(card, column)

        if role == Qt.TextAlignmentRole and column in (4, 5, 6):
            return Qt.AlignRight | Qt.AlignVCenter

        if role == Qt.ForegroundRole and column == 6:
            if card.remaining_balance == 0:
                return QColor("#999999")
            if card.remaining_balance < card.face_value:
                return QColor("#d97706")

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # noqa: N802
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def set_rows(self, rows: Sequence[GiftCard]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, row_index: int) -> GiftCard:
        return self._rows[row_index]

    def all_rows(self) -> List[GiftCard]:
        return list(self._rows)

    def _display_value(self, card: GiftCard, column: int):
        if column == 0:
            return card.sku
        if column == 1:
            return card.card_number
        if column == 2:
            return card.card_pin or ""
        if column == 3:
            return card.retailer.name if card.retailer else ""
        if column == 4:
            return self._format_currency(card.acquisition_cost)
        if column == 5:
            return self._format_currency(card.face_value)
        if column == 6:
            return self._format_currency(card.remaining_balance)
        return ""

    def _tooltip(self, card: GiftCard, column: int) -> str:
        if column == 1:
            return f"Card Number: {card.card_number}"
        if column == 2 and card.card_pin:
            return f"Pin: {card.card_pin}"
        return ""

    @staticmethod
    def _format_currency(value: Decimal | float | int | None) -> str:
        if value is None:
            return ""
        if isinstance(value, Decimal):
            return f"${value:.2f}"
        return f"${Decimal(value):.2f}"
