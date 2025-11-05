## Database Schema Overview

### Retailers (`retailers`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT UNIQUE NOT NULL
- `requires_pin` BOOLEAN NOT NULL DEFAULT 0
- `notes` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### Gift Cards (`gift_cards`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `retailer_id` INTEGER NOT NULL REFERENCES `retailers`(`id`) ON DELETE CASCADE
- `sku` TEXT UNIQUE NOT NULL
- `card_number` TEXT NOT NULL
- `card_pin` TEXT NULL
- `acquisition_cost` NUMERIC(10, 2) NOT NULL
- `face_value` NUMERIC(10, 2) NOT NULL
- `remaining_balance` NUMERIC(10, 2) NOT NULL
- `status` TEXT NOT NULL CHECK (`status` IN ('active', 'used', 'void', 'archived'))
- `purchase_date` DATE NULL
- `notes` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### Gift Card Usage (`gift_card_usage`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `gift_card_id` INTEGER NOT NULL REFERENCES `gift_cards`(`id`) ON DELETE CASCADE
- `order_id` INTEGER NULL REFERENCES `orders`(`id`) ON DELETE SET NULL
- `amount_used` NUMERIC(10, 2) NOT NULL CHECK (`amount_used` >= 0)
- `usage_date` DATETIME NOT NULL
- `created_at` DATETIME NOT NULL

### Orders (`orders`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `retailer_id` INTEGER NOT NULL REFERENCES `retailers`(`id`) ON DELETE RESTRICT
- `order_number` TEXT NOT NULL
- `order_date` DATE NOT NULL
- `order_email` TEXT NULL
- `payment_method` TEXT NOT NULL CHECK (`payment_method` IN ('gift_card', 'credit_card', 'mixed'))
- `subtotal` NUMERIC(10, 2) NOT NULL DEFAULT 0
- `tax` NUMERIC(10, 2) NOT NULL DEFAULT 0
- `shipping` NUMERIC(10, 2) NOT NULL DEFAULT 0
- `total_cost` NUMERIC(10, 2) NOT NULL
- `credit_card_spend` NUMERIC(10, 2) NOT NULL DEFAULT 0
- `gift_card_spend` NUMERIC(10, 2) NOT NULL DEFAULT 0
- `status` TEXT NOT NULL CHECK (`status` IN ('ordered', 'shipped', 'cancelled', 'delivered'))
- `receipt_path` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### Order Items (`order_items`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `order_id` INTEGER NOT NULL REFERENCES `orders`(`id`) ON DELETE CASCADE
- `item_name` TEXT NOT NULL
- `sku` TEXT NULL
- `upc` TEXT NULL
- `quantity` INTEGER NOT NULL CHECK (`quantity` > 0)
- `unit_price` NUMERIC(10, 2) NOT NULL
- `total_price` NUMERIC(10, 2) NOT NULL

### Inventory Items (`inventory_items`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `item_name` TEXT NOT NULL
- `sku` TEXT NULL UNIQUE
- `upc` TEXT NULL UNIQUE
- `quantity_on_hand` INTEGER NOT NULL DEFAULT 0
- `average_cost` NUMERIC(10, 4) NOT NULL DEFAULT 0
- `total_cost` NUMERIC(10, 2) NOT NULL DEFAULT 0
- `notes` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### Inventory Movements (`inventory_movements`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `inventory_item_id` INTEGER NOT NULL REFERENCES `inventory_items`(`id`) ON DELETE CASCADE
- `source_type` TEXT NOT NULL CHECK (`source_type` IN ('order', 'sale', 'adjustment'))
- `source_id` INTEGER NULL
- `quantity_change` INTEGER NOT NULL
- `cost_change` NUMERIC(10, 2) NOT NULL
- `movement_date` DATETIME NOT NULL
- `notes` TEXT NULL

### Sales (`sales`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `buyer` TEXT NULL
- `sale_date` DATE NOT NULL
- `total_value` NUMERIC(10, 2) NOT NULL
- `total_cost` NUMERIC(10, 2) NOT NULL
- `profit` NUMERIC(10, 2) NOT NULL
- `notes` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### Sale Items (`sale_items`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `sale_id` INTEGER NOT NULL REFERENCES `sales`(`id`) ON DELETE CASCADE
- `inventory_item_id` INTEGER NULL REFERENCES `inventory_items`(`id`) ON DELETE SET NULL
- `quantity` INTEGER NOT NULL CHECK (`quantity` > 0)
- `unit_price` NUMERIC(10, 2) NOT NULL
- `unit_cost` NUMERIC(10, 4) NOT NULL
- `line_total` NUMERIC(10, 2) NOT NULL
- `line_cost` NUMERIC(10, 2) NOT NULL

### Accounts (`accounts`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT UNIQUE NOT NULL
- `type` TEXT NOT NULL CHECK (`type` IN ('credit_card', 'bank', 'gift_card_pool'))
- `balance` NUMERIC(10, 2) NOT NULL DEFAULT 0
- `credit_limit` NUMERIC(10, 2) NULL
- `notes` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

### Account Transactions (`account_transactions`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `account_id` INTEGER NOT NULL REFERENCES `accounts`(`id`) ON DELETE CASCADE
- `related_type` TEXT NOT NULL CHECK (`related_type` IN ('order', 'sale', 'deposit', 'withdrawal'))
- `related_id` INTEGER NULL
- `amount` NUMERIC(10, 2) NOT NULL
- `description` TEXT NULL
- `transaction_date` DATETIME NOT NULL

### Attachments (`attachments`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `order_id` INTEGER NOT NULL REFERENCES `orders`(`id`) ON DELETE CASCADE
- `file_path` TEXT NOT NULL
- `label` TEXT NULL
- `created_at` DATETIME NOT NULL
- `updated_at` DATETIME NOT NULL

---

> **Note:** Date/time columns should use UTC timestamps. Application services will enforce SKU formatting, balance invariants, and automatic aggregate updates (e.g., inventory movement summaries, gift card remaining balances, account balances).
