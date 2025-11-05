"""Sales-related models."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


if TYPE_CHECKING:
    from .inventory import InventoryItem


class Sale(TimestampMixin, Base):
    """Represents a sale transaction."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer: Mapped[str | None] = mapped_column(String(255))
    sale_date: Mapped[date] = mapped_column(Date(), nullable=False)
    total_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    profit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))

    items: Mapped[List["SaleItem"]] = relationship(
        "SaleItem", back_populates="sale", cascade="all, delete-orphan"
    )


class SaleItem(Base):
    """Individual item sold within a sale."""

    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    inventory_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="SET NULL")
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    line_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    sale: Mapped[Sale] = relationship("Sale", back_populates="items")
    inventory_item: Mapped["InventoryItem" | None] = relationship(
        "InventoryItem", back_populates="sale_items"
    )
