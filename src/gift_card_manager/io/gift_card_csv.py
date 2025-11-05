"""CSV import/export utilities for gift cards.

These functions currently provide stub implementations that validate CSV
structure and either return parsed rows (import) or emit basic CSV output
from the database (export). They are intended to be expanded with richer
business rules, validation, and database integration as the application
workflow matures.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Sequence

from sqlalchemy.orm import Session

from ..models import GiftCard, Retailer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GiftCardCSVFormat:
    """Describes the expected CSV columns for a retailer."""

    retailer_code: str
    columns: Sequence[str]
    requires_pin: bool


@dataclass
class GiftCardImportRow:
    """Represents one gift card record parsed from a CSV file."""

    retailer_code: str
    card_number: str
    pin: str | None
    acquisition_cost: Decimal | None
    face_value: Decimal | None
    remaining_balance: Decimal | None


GIFT_CARD_FORMATS: dict[str, GiftCardCSVFormat] = {
    "BBY": GiftCardCSVFormat(
        retailer_code="BBY",
        columns=("card_number", "pin", "acquisition_cost", "face_value", "remaining_balance"),
        requires_pin=True,
    ),
    "DDR": GiftCardCSVFormat(
        retailer_code="DDR",
        columns=("card_number", "acquisition_cost", "face_value", "remaining_balance"),
        requires_pin=False,
    ),
    "LWS": GiftCardCSVFormat(
        retailer_code="LWS",
        columns=("card_number", "acquisition_cost", "face_value", "remaining_balance"),
        requires_pin=False,
    ),
    "HDP": GiftCardCSVFormat(
        retailer_code="HDP",
        columns=("card_number", "pin", "acquisition_cost", "face_value", "remaining_balance"),
        requires_pin=True,
    ),
    "AMZ": GiftCardCSVFormat(
        retailer_code="AMZ",
        columns=("card_number", "acquisition_cost", "face_value", "remaining_balance"),
        requires_pin=False,
    ),
}


def _normalise_code(retailer_code: str) -> str:
    code = retailer_code.strip().upper()
    if not code:
        raise ValueError("Retailer code must not be empty")
    return code


def _get_retailer(session: Session, retailer_code: str) -> Retailer:
    code = _normalise_code(retailer_code)
    retailer = session.query(Retailer).filter(Retailer.code == code).one_or_none()
    if retailer is None:
        raise ValueError(f"Retailer with code '{code}' not found in database")
    return retailer


def _get_format(retailer_code: str) -> GiftCardCSVFormat:
    code = _normalise_code(retailer_code)
    try:
        return GIFT_CARD_FORMATS[code]
    except KeyError as exc:
        raise ValueError(f"CSV format for retailer '{code}' is not defined") from exc


def import_gift_cards_from_csv(
    path: Path,
    retailer_code: str,
    session: Session,
) -> List[GiftCardImportRow]:
    """Parse a CSV file into structured gift card rows.

    The current implementation validates column headers and returns parsed rows
    without mutating the database. Higher-level services can use the returned
    data to perform additional validation or create `GiftCard` entities.
    """

    fmt = _get_format(retailer_code)
    retailer = _get_retailer(session, retailer_code)

    logger.info("Importing gift cards for retailer %s from %s", retailer.code, path)

    if not path.exists():
        raise FileNotFoundError(path)

    rows: List[GiftCardImportRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(fmt.columns) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"CSV file {path} is missing required columns: {', '.join(sorted(missing))}"
            )

        for idx, record in enumerate(reader, start=1):
            card_number = (record.get("card_number") or "").strip()
            pin_value = (record.get("pin") or "").strip()

            if not card_number:
                logger.warning("Row %s skipped: missing card_number", idx)
                continue

            if fmt.requires_pin and not pin_value:
                logger.warning("Row %s skipped: pin required for retailer %s", idx, retailer.code)
                continue

            row = GiftCardImportRow(
                retailer_code=retailer.code,
                card_number=card_number,
                pin=pin_value or None,
                acquisition_cost=_parse_decimal(record.get("acquisition_cost")),
                face_value=_parse_decimal(record.get("face_value")),
                remaining_balance=_parse_decimal(record.get("remaining_balance")),
            )
            rows.append(row)

    logger.info("Parsed %s gift card rows for retailer %s", len(rows), retailer.code)
    return rows


def export_gift_cards_to_csv(
    path: Path,
    retailer_code: str,
    session: Session,
) -> None:
    """Write gift cards for a retailer to a CSV file.

    The export currently includes all gift cards for the retailer. Filtering and
    formatting can be refined as requirements evolve.
    """

    fmt = _get_format(retailer_code)
    retailer = _get_retailer(session, retailer_code)

    logger.info("Exporting gift cards for retailer %s to %s", retailer.code, path)

    gift_cards: Iterable[GiftCard] = (
        session.query(GiftCard)
        .filter(GiftCard.retailer_id == retailer.id)
        .order_by(GiftCard.sku)
        .all()
    )

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fmt.columns)
        writer.writeheader()

        for card in gift_cards:
            row = {
                "card_number": card.card_number,
                "pin": card.card_pin or "",
                "acquisition_cost": _decimal_to_str(card.acquisition_cost),
                "face_value": _decimal_to_str(card.face_value),
                "remaining_balance": _decimal_to_str(card.remaining_balance),
            }

            if not fmt.requires_pin:
                row.pop("pin", None)

            writer.writerow(row)

    logger.info("Export completed for retailer %s", retailer.code)


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except ArithmeticError:
        logger.warning("Could not parse decimal from value '%s'", value)
        return None


def _decimal_to_str(value: Decimal | float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)
