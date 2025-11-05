"""Account tracking models."""

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import AccountRelatedType, AccountType


class Account(TimestampMixin, Base):
    """Represents a payment account such as a credit card."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    credit_limit: Mapped[float | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(String(500))

    transactions: Mapped[List["AccountTransaction"]] = relationship(
        "AccountTransaction", back_populates="account", cascade="all, delete-orphan"
    )


class AccountTransaction(Base):
    """Individual transaction affecting an account balance."""

    __tablename__ = "account_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    related_type: Mapped[AccountRelatedType] = mapped_column(Enum(AccountRelatedType), nullable=False)
    related_id: Mapped[int | None]
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped[Account] = relationship("Account", back_populates="transactions")

