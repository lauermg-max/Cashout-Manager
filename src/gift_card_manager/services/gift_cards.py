"""Gift card service logic."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from ..models import GiftCard, Retailer
from ..utils import generate_gift_card_sku


class GiftCardService:
    """Encapsulates gift card operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_gift_cards(self) -> Iterable[GiftCard]:
        """Return all gift cards ordered by retailer."""

        return (
            self.session.query(GiftCard)
            .order_by(GiftCard.retailer_id, GiftCard.sku)
            .all()
        )

    def create_gift_card(self, gift_card: GiftCard) -> GiftCard:
        """Persist a new gift card."""

        if not gift_card.sku:
            retailer: Retailer | None = gift_card.retailer
            if retailer is None and gift_card.retailer_id is not None:
                retailer = self.session.get(Retailer, gift_card.retailer_id)
            if retailer is None:
                raise ValueError("Retailer information is required to generate a SKU")
            gift_card.sku = generate_gift_card_sku(self.session, retailer)

        self.session.add(gift_card)
        self.session.flush()
        return gift_card
