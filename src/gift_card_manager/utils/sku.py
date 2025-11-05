"""Helpers for generating unique SKUs."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import GiftCard, Retailer


def generate_gift_card_sku(session: Session, retailer: Retailer) -> str:
    """Generate a unique SKU for a retailer's gift card."""

    date_part = date.today().strftime("%Y%m%d")
    prefix = f"{retailer.code}-{date_part}"

    existing = session.execute(
        select(GiftCard.sku)
        .where(
            GiftCard.retailer_id == retailer.id,
            GiftCard.sku.like(f"{prefix}-%"),
        )
        .order_by(GiftCard.sku.desc())
        .limit(1)
    ).scalar_one_or_none()

    if existing:
        try:
            last_number = int(existing.split("-")[-1])
        except ValueError:
            last_number = 0
        sequence = last_number + 1
    else:
        sequence = 1

    return f"{prefix}-{sequence:04d}"
