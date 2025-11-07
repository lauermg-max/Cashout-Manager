"""Inventory management services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import InventoryItem, InventoryMovement
from ..models.enums import InventorySourceType


@dataclass(frozen=True)
class InventoryAdjustment:
    """Represents a quantity/cost change applied to an inventory item."""

    quantity_change: int
    cost_change: Decimal
    source_type: InventorySourceType
    source_id: int | None = None
    order_item_id: int | None = None
    notes: str | None = None


class InventoryService:
    """Encapsulates inventory item and movement logic."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ---------------------------------------------------------------- Items
    def create_item(
        self,
        item: InventoryItem,
        *,
        initial_adjustment: InventoryAdjustment | None = None,
    ) -> InventoryItem:
        self.session.add(item)
        self.session.flush()

        if initial_adjustment:
            self.apply_adjustment(item, initial_adjustment)

        return item

    def update_item(self, item: InventoryItem) -> InventoryItem:
        self.session.flush()
        return item

    def delete_item(self, item: InventoryItem) -> None:
        for movement in list(item.movements):
            self.session.delete(movement)
        self.session.delete(item)

    # ------------------------------------------------------------- Movements
    def apply_adjustment(
        self,
        item: InventoryItem,
        adjustment: InventoryAdjustment,
        *,
        movement_date: datetime | None = None,
    ) -> InventoryMovement:
        if adjustment.quantity_change == 0 and adjustment.cost_change == Decimal("0"):
            raise ValueError("Adjustment must change quantity or cost")

        movement = InventoryMovement(
            inventory_item_id=item.id,
            source_type=adjustment.source_type,
            source_id=adjustment.source_id,
            order_item_id=adjustment.order_item_id,
            quantity_change=adjustment.quantity_change,
            cost_change=adjustment.cost_change,
            movement_date=movement_date or datetime.utcnow(),
            notes=adjustment.notes,
        )
        self.session.add(movement)

        self._apply_to_item(item, adjustment)
        return movement

    def _apply_to_item(self, item: InventoryItem, adjustment: InventoryAdjustment) -> None:
        quantity_change = adjustment.quantity_change or 0
        cost_change = adjustment.cost_change or Decimal("0")

        new_quantity = (item.quantity_on_hand or 0) + quantity_change
        if new_quantity < 0:
            raise ValueError("Inventory quantity cannot be negative")

        new_total_cost = (item.total_cost or Decimal("0")) + cost_change
        if new_total_cost < 0:
            raise ValueError("Inventory total cost cannot be negative")

        item.quantity_on_hand = new_quantity
        item.total_cost = new_total_cost.quantize(Decimal("0.01"))

        if new_quantity > 0:
            item.average_cost = (item.total_cost / Decimal(new_quantity)).quantize(Decimal("0.0001"))
        else:
            item.average_cost = Decimal("0")

        item.notes = item.notes  # trigger dirty flag

