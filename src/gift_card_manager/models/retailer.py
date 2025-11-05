"""Retailer model."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


if TYPE_CHECKING:
    from .gift_card import GiftCard
    from .order import Order


class Retailer(TimestampMixin, Base):
    """Represents a retailer with specific gift card format rules."""

    __tablename__ = "retailers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    requires_pin: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))

    gift_cards: Mapped[List["GiftCard"]] = relationship("GiftCard", back_populates="retailer")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="retailer")
