"""Inventory-related models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import InventorySourceType


if TYPE_CHECKING:
    from .order import OrderItem
    from .sales import SaleItem


class InventoryItem(TimestampMixin, Base):
    """Represents an item tracked in physical inventory."""

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64), unique=True)
    upc: Mapped[str | None] = mapped_column(String(64), unique=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_cost: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String(500))

    movements: Mapped[List["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="inventory_item", cascade="all, delete-orphan"
    )
    sale_items: Mapped[List["SaleItem"]] = relationship("SaleItem", back_populates="inventory_item")


class InventoryMovement(Base):
    """Tracks adjustments that affect inventory levels."""

    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[InventorySourceType] = mapped_column(
        Enum(InventorySourceType), nullable=False
    )
    source_id: Mapped[int | None]
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id", ondelete="SET NULL"))
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_change: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    movement_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(500))

    inventory_item: Mapped[InventoryItem] = relationship("InventoryItem", back_populates="movements")
    order_item: Mapped["OrderItem" | None] = relationship("OrderItem", back_populates="inventory_links")
