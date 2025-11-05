# Development Environment Setup

## Virtual Environment and Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## Running the Application
```bash
python -m gift_card_manager
# or
python src/gift_card_manager/app.py
```

## Database Migrations
```bash
alembic upgrade head
alembic revision -m "describe change"
```

### Resetting the SQLite Database
Delete `C:\Users\<you>\.gift_card_manager\gift_card_manager.sqlite3` and rerun the app to recreate with the latest schema.

## CSV Utilities (Work in Progress)
- `import_gift_cards_from_csv(path, retailer_code, session)` parses CSV data into structured rows without committing to the database.
- `export_gift_cards_to_csv(path, retailer_code, session)` writes gift cards for a retailer to a CSV file.

Retailer formats currently cover Best Buy, Doordash, Lowe's, Home Depot, and Amazon (`src/gift_card_manager/io/gift_card_csv.py`).

## Orders UI Notes
- Orders tab uses `OrderService` to maintain gift card balances when orders are created, edited, or deleted.
- Gift card allocations are captured via the order dialog; insufficient balances raise validation errors from the service layer.

## Inventory UI Notes
- Inventory tab uses `InventoryService` to apply stock adjustments and maintain average cost.
- Manual adjustments require either a quantity change or cost change; negative balances are prevented by service-level validation.

## Static Checks
```bash
python -m compileall src
```
