"""Order-related models."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import OrderStatus, PaymentMethod


if TYPE_CHECKING:
    from .gift_card import GiftCardUsage
    from .inventory import InventoryMovement
    from .retailer import Retailer


class Order(TimestampMixin, Base):
    """Represents an order placed with retailers."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id", ondelete="RESTRICT"), nullable=False)
    order_number: Mapped[str] = mapped_column(String(100), nullable=False)
    order_date: Mapped[date] = mapped_column(Date(), nullable=False)
    order_email: Mapped[str | None] = mapped_column(String(200))
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    tax: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    shipping: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    credit_card_spend: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    gift_card_spend: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.ORDERED)
    receipt_path: Mapped[str | None] = mapped_column(String(500))

    retailer: Mapped["Retailer"] = relationship("Retailer", back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    gift_cards_used: Mapped[List["GiftCardUsage"]] = relationship(
        "GiftCardUsage", back_populates="order"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    """Line item within an order."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100))
    upc: Mapped[str | None] = mapped_column(String(64))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="items")
    inventory_links: Mapped[List["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="order_item"
    )


class Attachment(TimestampMixin, Base):
    """Files linked to an order (e.g., receipts)."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(200))

    order: Mapped[Order] = relationship("Order", back_populates="attachments")
