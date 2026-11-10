# Database Design — Synthetic Retail Sales

**Status:** Schema and seed SQL are present. Their application to a fresh PostgreSQL database has not been verified.

## Source of truth

- `src/text_to_sql_agent/db_scripts/001_schema.sql` defines the current retail schema.
- `src/text_to_sql_agent/db_scripts/002_seed.sql` defines deterministic sample rows.
- `src/text_to_sql_agent/app/db/models.py` maps `schema_documents` as a SQLAlchemy model.
- `migrations/versions/ef3a65e3fc1f_create_schema_documents.py` creates that table and its indexes.
- Alembic is configured for async PostgreSQL connections; the retail schema and seed data remain SQL bootstrap scripts.
- `.database/init/01-init.sh` currently creates an application database and user only. Docker Compose does not mount or execute the schema and seed SQL files.

## Tables and relationships

| Table | Columns |
|---|---|
| `customers` | `customer_id`, `customer_name`, `region` |
| `products` | `product_id`, `product_name`, `category` |
| `orders` | `order_id`, `customer_id`, `order_date`, `status` |
| `order_items` | `order_item_id`, `order_id`, `product_id`, `quantity`, `unit_price`, `discount_pct` |

- `orders.customer_id` references `customers.customer_id`.
- `order_items.order_id` references `orders.order_id`.
- `order_items.product_id` references `products.product_id`.
- Orders are restricted to `completed` or `cancelled`.
- Quantity must be positive, unit price non-negative, and `discount_pct` between 0 and 1.

## Business semantics present in code/data

- Gross line value: `quantity * unit_price`.
- Net line value: `quantity * unit_price * (1 - discount_pct)`.
- Golden reference queries treat completed orders as recognized revenue and exclude cancelled orders, except the cancellation reconciliation case.
- Date intervals use an inclusive start and exclusive end in the schema context and golden SQL.
- Currency units are not explicitly documented in the schema or seed data.

## Setup and design gaps

- Make Compose initialization apply the schema and seed files in a repeatable, ordered way.
- Decide and implement a least-privilege read-only query role; the current init script grants the application user all database privileges.
- Add a fresh-database smoke test and verify seed row counts and foreign-key/check constraints.
- Extend the migration strategy to the retail tables before treating Alembic as the complete database setup path.
- Keep metric, currency, date, and tie-breaking semantics explicit as golden cases are expanded.
