"""Order service logic, including gift card allocations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy.orm import Session

from ..models import GiftCard, GiftCardUsage, Order
from ..models.enums import GiftCardStatus


@dataclass(frozen=True)
class GiftCardAllocation:
    """Represents an amount to deduct from a specific gift card."""

    gift_card_id: int
    amount: Decimal


class OrderService:
    """Encapsulates order workflows and gift card balance updates."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ CRUD --
    def create_order(
        self,
        order: Order,
        *,
        allocations: Sequence[GiftCardAllocation] | None = None,
    ) -> Order:
        """Persist a new order and apply optional gift card allocations."""

        self.session.add(order)
        self.session.flush()

        if allocations:
            self._apply_gift_card_allocations(order, allocations)

        return order

    def delete_order(self, order: Order) -> None:
        """Delete an order and restore any related gift card balances."""

        self._restore_gift_cards(order)
        self.session.flush()
        self.session.delete(order)

    # ---------------------------------------------------- Gift card usage --
    def update_gift_card_allocations(
        self,
        order: Order,
        allocations: Sequence[GiftCardAllocation],
    ) -> None:
        """Replace the gift card usage for an order with new allocations."""

        self._restore_gift_cards(order)
        self.session.flush()

        for usage in list(order.gift_cards_used):
            self.session.delete(usage)

        self._apply_gift_card_allocations(order, allocations)

    def _apply_gift_card_allocations(
        self,
        order: Order,
        allocations: Sequence[GiftCardAllocation],
    ) -> None:
        """Deduct the specified amounts from each gift card and link to the order."""

        total_allocated = Decimal("0")
        for allocation in allocations:
            amount = self._validate_amount(allocation.amount)
            card = self._get_gift_card(allocation.gift_card_id)

            if card.remaining_balance is None:
                card.remaining_balance = Decimal("0")

            if amount > card.remaining_balance:
                raise ValueError(
                    f"Gift card {card.sku} does not have enough balance."
                )

            card.remaining_balance -= amount
            self._apply_status(card)

            usage = GiftCardUsage(
                gift_card_id=card.id,
                order_id=order.id,
                amount_used=amount,
                usage_date=date.today(),
            )
            self.session.add(usage)
            total_allocated += amount

        order.gift_card_spend = total_allocated

    def _restore_gift_cards(self, order: Order) -> None:
        """Return previously applied usage amounts back to gift cards."""

        for usage in list(order.gift_cards_used):
            card = usage.gift_card
            if card is None:
                card = self.session.get(GiftCard, usage.gift_card_id)
            if card is None:
                continue
            if card.remaining_balance is None:
                card.remaining_balance = Decimal("0")
            card.remaining_balance += Decimal(usage.amount_used)
            self._apply_status(card)

    # ------------------------------------------------------------- Helpers --
    def _get_gift_card(self, gift_card_id: int) -> GiftCard:
        card = self.session.get(GiftCard, gift_card_id)
        if card is None:
            raise ValueError(f"Gift card id {gift_card_id} does not exist")
        return card

    @staticmethod
    def _validate_amount(amount: Decimal) -> Decimal:
        if amount is None:
            raise ValueError("Gift card allocation amount is required")
        amount = Decimal(amount).quantize(Decimal("0.01"))
        if amount <= 0:
            raise ValueError("Gift card allocation amount must be positive")
        return amount

    @staticmethod
    def _apply_status(card: GiftCard) -> None:
        if card.remaining_balance is None or card.remaining_balance == 0:
            card.status = GiftCardStatus.USED
        else:
            card.status = GiftCardStatus.ACTIVE
