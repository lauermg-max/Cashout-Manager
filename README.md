# Gift Card Manager

Desktop application for tracking discounted gift cards, orders, inventory, sales, and analytics. The app targets Windows and will ship as a standalone `.exe` using PySide6 for the GUI and SQLite for storage.

## Features (Planned)
- Gift card inventory with CSV import/export per retailer (Doordash, Best Buy, Lowe's, Home Depot, Amazon).
- Orders module with receipt attachments, gift card usage tracking, and CSV import/export.
- Physical inventory tracking tied to delivered orders and manual adjustments.
- Sales tracking with profit reporting.
- Analytics dashboard summarizing balances, status counts, and time-filtered stats.
- Accounts view covering credit cards and other payment sources.

## Tech Stack
- Python 3.11+
- PySide6 (Qt GUI)
- SQLAlchemy + SQLite (data storage)
- Alembic (migrations)
- Pydantic (validation)
- Pandas (CSV import/export)
- PyInstaller (Windows packaging)

## Repository Structure
```
docs/                # Specifications and design documents
src/gift_card_manager/
  core/              # settings, db engine, utilities
  models/            # SQLAlchemy ORM models
  services/          # business logic services
  ui/                # Qt widgets, dialogs, and views
  io/                # CSV import/export helpers
  utils/             # shared helpers (formatting, validators, etc.)
assets/              # Icons, themes, static files
migrations/          # Alembic migrations
tests/               # Automated tests
```

## Getting Started
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m gift_card_manager
```

> **Note:** Requirements list and application entry point will be added as the implementation progresses.

## Documentation
- `docs/schema.md` — current database schema blueprint.

## Packaging (Planned)
```bash
pyinstaller --name GiftCardManager --onefile src/gift_card_manager/app.py
```

Further packaging scripts will be introduced once the core UI is implemented.
