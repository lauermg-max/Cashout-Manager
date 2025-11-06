"""Order service logic, including gift card allocations and inventory sync."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

from ..models import (
    GiftCard,
    GiftCardUsage,
    InventoryItem,
    InventoryMovement,
    Order,
    OrderItem,
)
from ..models.enums import GiftCardStatus, InventorySourceType, OrderStatus
from .inventory import InventoryAdjustment, InventoryService


logger = logging.getLogger(__name__)


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

        self._sync_inventory_for_status(order, previous_status=None)

        return order

    def delete_order(self, order: Order) -> None:
        """Delete an order and restore any related gift card balances."""

        self._reverse_order_restock(order)
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

        previous_status = self._previous_status(order)

        self._restore_gift_cards(order)
        self.session.flush()

        for usage in list(order.gift_cards_used):
            self.session.delete(usage)

        self._apply_gift_card_allocations(order, allocations)
        self._sync_inventory_for_status(order, previous_status=previous_status)

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

    # ---------------------------------------------------- Inventory sync --
    def _sync_inventory_for_status(
        self,
        order: Order,
        *,
        previous_status: OrderStatus | None,
    ) -> None:
        """Adjust inventory movements based on order status transitions."""

        current_status = order.status
        if current_status == OrderStatus.DELIVERED:
            if previous_status != OrderStatus.DELIVERED:
                self._apply_order_restock(order)
        elif previous_status == OrderStatus.DELIVERED and current_status != OrderStatus.DELIVERED:
            self._reverse_order_restock(order)

    def _apply_order_restock(self, order: Order) -> None:
        """Add delivered order quantities into physical inventory."""

        if not order.items:
            return

        inventory_service = InventoryService(self.session)

        for order_item in list(order.items):
            if order_item.quantity <= 0:
                continue

            if self._has_existing_order_movement(order, order_item):
                continue

            inventory_item = self._get_or_create_inventory_item(order_item)
            if inventory_item is None:
                continue

            cost_change = self._to_decimal(order_item.total_price)
            if cost_change == Decimal("0"):
                unit_price = self._to_decimal(order_item.unit_price)
                cost_change = unit_price * Decimal(order_item.quantity)

            adjustment = InventoryAdjustment(
                quantity_change=order_item.quantity,
                cost_change=cost_change,
                source_type=InventorySourceType.ORDER,
                source_id=order.id,
                order_item_id=order_item.id,
                notes=f"Order {order.order_number} delivered",
            )

            try:
                inventory_service.apply_adjustment(inventory_item, adjustment)
            except Exception:  # pragma: no cover - safety log for UI
                logger.exception("Failed to restock inventory for order %s", order.id)

    def _reverse_order_restock(self, order: Order) -> None:
        """Remove prior restock movements when an order is undone."""

        movements = self.session.execute(
            select(InventoryMovement)
            .where(
                InventoryMovement.source_type == InventorySourceType.ORDER,
                InventoryMovement.source_id == order.id,
            )
            .order_by(InventoryMovement.id.asc())
        ).scalars().all()

        if not movements:
            return

        inventory_service = InventoryService(self.session)

        for movement in movements:
            inventory_item = movement.inventory_item
            if inventory_item is None:
                inventory_item = self.session.get(InventoryItem, movement.inventory_item_id)
            if inventory_item is None:
                logger.warning(
                    "Inventory item %s missing while reversing order %s", movement.inventory_item_id, order.id
                )
                continue

            adjustment = InventoryAdjustment(
                quantity_change=-movement.quantity_change,
                cost_change=-self._to_decimal(movement.cost_change),
                source_type=InventorySourceType.ORDER,
                source_id=order.id,
                order_item_id=movement.order_item_id,
                notes=f"Reverse order {order.order_number} restock",
            )

            try:
                reversal_movement = inventory_service.apply_adjustment(inventory_item, adjustment)
            except Exception:  # pragma: no cover - safety log for UI
                logger.exception("Failed to reverse restock for order %s", order.id)
                continue

            self.session.delete(movement)
            self.session.delete(reversal_movement)

    def _has_existing_order_movement(self, order: Order, order_item: OrderItem) -> bool:
        return (
            self.session.execute(
                select(InventoryMovement.id)
                .where(
                    InventoryMovement.source_type == InventorySourceType.ORDER,
                    InventoryMovement.source_id == order.id,
                    InventoryMovement.order_item_id == order_item.id,
                )
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )

    def _get_or_create_inventory_item(self, order_item: OrderItem) -> InventoryItem | None:
        if order_item.sku:
            stmt = select(InventoryItem).where(InventoryItem.sku == order_item.sku)
        elif order_item.upc:
            stmt = select(InventoryItem).where(InventoryItem.upc == order_item.upc)
        else:
            stmt = select(InventoryItem).where(InventoryItem.item_name == order_item.item_name)

        inventory_item = self.session.execute(stmt.limit(1)).scalar_one_or_none()
        if inventory_item:
            return inventory_item

        inventory_item = InventoryItem(
            item_name=order_item.item_name,
            sku=order_item.sku,
            upc=order_item.upc,
        )
        self.session.add(inventory_item)
        self.session.flush()
        return inventory_item

    def _previous_status(self, order: Order) -> OrderStatus | None:
        history = get_history(order, "status")
        if history.deleted:
            return history.deleted[0]
        if history.unchanged:
            return history.unchanged[0]
        return None

    @staticmethod
    def _to_decimal(value) -> Decimal:
        if value is None:
            return Decimal("0")
        return Decimal(str(value)).quantize(Decimal("0.01"))
