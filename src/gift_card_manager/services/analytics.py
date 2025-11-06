"""Analytics aggregation services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import GiftCard, Order, Retailer, Sale
from ..models.enums import OrderStatus


@dataclass
class GiftCardSummary:
    remaining_balance: Decimal
    acquisition_cost: Decimal


@dataclass
class OrderStatusSummary:
    ordered: int
    shipped: int
    cancelled: int
    delivered: int


@dataclass
class SalesSummary:
    total_value: Decimal
    total_cost: Decimal
    profit: Decimal


class AnalyticsService:
    """Provides aggregated metrics for analytics dashboards."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # --------------------------------------------------------- Gift Cards --
    def gift_card_summary(self, retailer_code: Optional[str] = None) -> GiftCardSummary:
        query = self.session.query(
            func.coalesce(func.sum(GiftCard.remaining_balance), 0),
            func.coalesce(func.sum(GiftCard.acquisition_cost), 0),
        )
        if retailer_code and retailer_code != "ALL":
            query = query.join(Retailer).filter(Retailer.code == retailer_code)
        remaining, cost = query.one()
        return GiftCardSummary(
            remaining_balance=Decimal(remaining).quantize(Decimal("0.01")),
            acquisition_cost=Decimal(cost).quantize(Decimal("0.01")),
        )

    # ------------------------------------------------------------- Orders --
    def order_status_summary(
        self,
        *,
        retailer_code: Optional[str] = None,
        start_date: Optional[date] = None,
    ) -> OrderStatusSummary:
        query = self.session.query(Order.status, func.count(Order.id))
        if retailer_code and retailer_code != "ALL":
            query = query.join(Retailer).filter(Retailer.code == retailer_code)
        if start_date:
            query = query.filter(Order.order_date >= start_date)
        query = query.group_by(Order.status)

        counts = {status: 0 for status in OrderStatus}
        for status, count in query.all():
            counts[status] = count

        return OrderStatusSummary(
            ordered=counts[OrderStatus.ORDERED],
            shipped=counts[OrderStatus.SHIPPED],
            cancelled=counts[OrderStatus.CANCELLED],
            delivered=counts[OrderStatus.DELIVERED],
        )

    # -------------------------------------------------------------- Sales --
    def sales_summary(
        self,
        *,
        start_date: Optional[date] = None,
    ) -> SalesSummary:
        query = self.session.query(
            func.coalesce(func.sum(Sale.total_value), 0),
            func.coalesce(func.sum(Sale.total_cost), 0),
            func.coalesce(func.sum(Sale.profit), 0),
        )
        if start_date:
            query = query.filter(Sale.sale_date >= start_date)
        value, cost, profit = query.one()
        return SalesSummary(
            total_value=Decimal(value).quantize(Decimal("0.01")),
            total_cost=Decimal(cost).quantize(Decimal("0.01")),
            profit=Decimal(profit).quantize(Decimal("0.01")),
        )

    # ----------------------------------------------------------- Utilities --
    @staticmethod
    def timeframe_start(reference: datetime, timeframe: str) -> Optional[date]:
        timeframe_map = {
            "24h": timedelta(days=1),
            "3d": timedelta(days=3),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "3m": timedelta(days=90),
            "6m": timedelta(days=180),
            "12m": timedelta(days=365),
        }
        if timeframe in (None, "all"):
            return None
        delta = timeframe_map.get(timeframe)
        if not delta:
            return None
        start_datetime = reference - delta
        return start_datetime.date()
