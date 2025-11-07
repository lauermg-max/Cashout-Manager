"""Database bootstrap helpers."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from ..models import Retailer
from .db import engine, session_scope


DEFAULT_RETAILERS: Iterable[dict[str, object]] = (
    {"code": "BBY", "name": "Best Buy", "requires_pin": True},
    {"code": "DDR", "name": "Doordash", "requires_pin": False},
    {"code": "LWS", "name": "Lowe's", "requires_pin": False},
    {"code": "HDP", "name": "Home Depot", "requires_pin": True},
    {"code": "AMZ", "name": "Amazon", "requires_pin": False},
)


def bootstrap_database() -> None:
    """Ensure required reference data exists in the database."""

    with session_scope() as session:
        existing_codes: set[str]
        try:
            existing_codes = {
                code for (code,) in session.execute(select(Retailer.code)).all()
                if code is not None
            }
        except OperationalError:
            _ensure_retailer_code_column()
            existing_codes = {
                code for (code,) in session.execute(select(Retailer.code)).all()
                if code is not None
            }

        for retailer_data in DEFAULT_RETAILERS:
            code = retailer_data["code"]
            if code in existing_codes:
                continue
            session.add(Retailer(**retailer_data))


def _ensure_retailer_code_column() -> None:
    """Add the retailer code column if this is an older database."""

    with engine.begin() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(retailers)")).fetchall()
        }
        if "code" in columns:
            return

        connection.execute(text("ALTER TABLE retailers ADD COLUMN code TEXT"))

        rows = connection.execute(text("SELECT id, name FROM retailers")).fetchall()
        seen_codes: set[str] = set()
        for idx, row in enumerate(rows, start=1):
            base_code = _suggest_retailer_code(row[1])
            code = base_code
            counter = 1
            while code in seen_codes:
                code = f"{base_code}{counter}"
                counter += 1
            seen_codes.add(code)
            connection.execute(
                text("UPDATE retailers SET code = :code WHERE id = :id"),
                {"code": code, "id": row[0]},
            )


def _suggest_retailer_code(name: str) -> str:
    slug = "".join(ch for ch in name.upper() if ch.isalnum())
    if not slug:
        slug = "RET"
    return slug[:3] if len(slug) >= 3 else slug.ljust(3, "X")
