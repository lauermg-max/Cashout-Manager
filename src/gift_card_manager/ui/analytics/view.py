"""Analytics dashboard view."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...core import session_scope
from ...models import Retailer
from ...services import AnalyticsService


class AnalyticsView(QWidget):
    """Displays aggregate stats for gift cards, orders, and sales."""

    TIMEFRAME_OPTIONS = [
        ("All time", "all"),
        ("Last 24 hours", "24h"),
        ("Last 3 days", "3d"),
        ("Last 7 days", "7d"),
        ("Last 30 days", "30d"),
        ("Last 3 months", "3m"),
        ("Last 6 months", "6m"),
        ("Last 12 months", "12m"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._timeframe_combo = QComboBox()
        for label, value in self.TIMEFRAME_OPTIONS:
            self._timeframe_combo.addItem(label, value)

        self._retailer_combo = QComboBox()

        self._gift_remaining_label = QLabel("$0.00")
        self._gift_cost_label = QLabel("$0.00")

        self._orders_ordered_label = QLabel("0")
        self._orders_shipped_label = QLabel("0")
        self._orders_cancelled_label = QLabel("0")
        self._orders_delivered_label = QLabel("0")

        self._sales_value_label = QLabel("$0.00")
        self._sales_cost_label = QLabel("$0.00")
        self._sales_profit_label = QLabel("$0.00")

        layout = QVBoxLayout()
        layout.addLayout(self._build_filters())
        layout.addWidget(self._build_gift_card_group())
        layout.addWidget(self._build_orders_group())
        layout.addWidget(self._build_sales_group())
        layout.addStretch(1)
        self.setLayout(layout)

        self._timeframe_combo.currentIndexChanged.connect(self.refresh)
        self._retailer_combo.currentIndexChanged.connect(self.refresh)

        self._load_retailers()
        self.refresh()

    def _build_filters(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Timeframe:"))
        row.addWidget(self._timeframe_combo, 1)
        row.addSpacing(16)
        row.addWidget(QLabel("Retailer:"))
        row.addWidget(self._retailer_combo, 1)
        row.addStretch(1)
        return row

    def _build_gift_card_group(self) -> QGroupBox:
        group = QGroupBox("Gift Cards")
        form = QFormLayout()
        form.addRow("Remaining Balance", self._gift_remaining_label)
        form.addRow("Acquisition Cost", self._gift_cost_label)
        group.setLayout(form)
        return group

    def _build_orders_group(self) -> QGroupBox:
        group = QGroupBox("Orders")
        form = QFormLayout()
        form.addRow("Ordered", self._orders_ordered_label)
        form.addRow("Shipped", self._orders_shipped_label)
        form.addRow("Cancelled", self._orders_cancelled_label)
        form.addRow("Delivered", self._orders_delivered_label)
        group.setLayout(form)
        return group

    def _build_sales_group(self) -> QGroupBox:
        group = QGroupBox("Sales")
        form = QFormLayout()
        form.addRow("Total Value", self._sales_value_label)
        form.addRow("Total Cost", self._sales_cost_label)
        form.addRow("Profit", self._sales_profit_label)
        group.setLayout(form)
        return group

    def _load_retailers(self) -> None:
        self._retailer_combo.blockSignals(True)
        self._retailer_combo.clear()
        self._retailer_combo.addItem("All Retailers", "ALL")
        with session_scope() as session:
            retailers = session.query(Retailer).order_by(Retailer.name).all()
        for retailer in retailers:
            self._retailer_combo.addItem(f"{retailer.name} ({retailer.code})", retailer.code)
        self._retailer_combo.blockSignals(False)

    def refresh(self) -> None:
        timeframe = self._timeframe_combo.currentData(Qt.ItemDataRole.UserRole)
        retailer_code = self._retailer_combo.currentData(Qt.ItemDataRole.UserRole)

        with session_scope() as session:
            service = AnalyticsService(session)
            start_date = service.timeframe_start(datetime.utcnow(), timeframe)

            gift_summary = service.gift_card_summary(retailer_code)
            order_summary = service.order_status_summary(retailer_code=retailer_code, start_date=start_date)
            sales_summary = service.sales_summary(start_date=start_date)

        self._gift_remaining_label.setText(f"${gift_summary.remaining_balance:.2f}")
        self._gift_cost_label.setText(f"${gift_summary.acquisition_cost:.2f}")

        self._orders_ordered_label.setText(str(order_summary.ordered))
        self._orders_shipped_label.setText(str(order_summary.shipped))
        self._orders_cancelled_label.setText(str(order_summary.cancelled))
        self._orders_delivered_label.setText(str(order_summary.delivered))

        self._sales_value_label.setText(f"${sales_summary.total_value:.2f}")
        self._sales_cost_label.setText(f"${sales_summary.total_cost:.2f}")
        self._sales_profit_label.setText(f"${sales_summary.profit:.2f}")
