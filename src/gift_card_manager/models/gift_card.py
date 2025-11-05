"""Gift card model."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import GiftCardStatus


if TYPE_CHECKING:
    from .order import Order
    from .retailer import Retailer


class GiftCard(TimestampMixin, Base):
    """Represents a single gift card and its current balance."""

    __tablename__ = "gift_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id", ondelete="CASCADE"), nullable=False)
    sku: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    card_number: Mapped[str] = mapped_column(String(128), nullable=False)
    card_pin: Mapped[str | None] = mapped_column(String(64))
    acquisition_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    face_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    remaining_balance: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[GiftCardStatus] = mapped_column(Enum(GiftCardStatus), nullable=False, default=GiftCardStatus.ACTIVE)
    purchase_date: Mapped[date | None] = mapped_column(Date())
    notes: Mapped[str | None] = mapped_column(String(500))

    retailer: Mapped["Retailer"] = relationship("Retailer", back_populates="gift_cards")
    usages: Mapped[List["GiftCardUsage"]] = relationship("GiftCardUsage", back_populates="gift_card", cascade="all, delete-orphan")


class GiftCardUsage(TimestampMixin, Base):
    """Logs deductions against a gift card."""

    __tablename__ = "gift_card_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    gift_card_id: Mapped[int] = mapped_column(ForeignKey("gift_cards.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    amount_used: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    usage_date: Mapped[date] = mapped_column(Date(), nullable=False, default=date.today)

    gift_card: Mapped[GiftCard] = relationship("GiftCard", back_populates="usages")
    order: Mapped["Order" | None] = relationship("Order", back_populates="gift_cards_used")


if TYPE_CHECKING:
    from .retailer import Retailer
