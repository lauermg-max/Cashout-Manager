"""Enum definitions shared across models."""

from enum import Enum


class GiftCardStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    VOID = "void"
    ARCHIVED = "archived"


class PaymentMethod(str, Enum):
    GIFT_CARD = "gift_card"
    CREDIT_CARD = "credit_card"
    MIXED = "mixed"


class OrderStatus(str, Enum):
    ORDERED = "ordered"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"


class InventorySourceType(str, Enum):
    ORDER = "order"
    SALE = "sale"
    ADJUSTMENT = "adjustment"


class AccountType(str, Enum):
    CREDIT_CARD = "credit_card"
    BANK = "bank"
    GIFT_CARD_POOL = "gift_card_pool"


class AccountRelatedType(str, Enum):
    ORDER = "order"
    SALE = "sale"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
