
from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaDocument:
    """A single retrievable unit of schema knowledge."""

    document_id: str
    category: str
    title: str
    content: str


SCHEMA_DOCUMENTS: tuple[SchemaDocument, ...] = (
    SchemaDocument(
        document_id="table_customers",
        category="table",
        title="Customers table",
        content=(
            "Table: customers. "
            "Columns: customer_id (primary key), "
            "customer_name, region. "
            "Stores customer master data and the customer's region."
        ),
    ),
    SchemaDocument(
        document_id="table_products",
        category="table",
        title="Products table",
        content=(
            "Table: products. "
            "Columns: product_id (primary key), "
            "product_name, category. "
            "Stores product master data and product categories."
        ),
    ),
    SchemaDocument(
        document_id="table_orders",
        category="table",
        title="Orders table",
        content=(
            "Table: orders. "
            "Columns: order_id (primary key), "
            "customer_id (foreign key to customers.customer_id), "
            "order_date, status. "
            "Allowed order statuses are completed and cancelled. "
            "Each order belongs to one customer."
        ),
    ),
    SchemaDocument(
        document_id="table_order_items",
        category="table",
        title="Order items table",
        content=(
            "Table: order_items. "
            "Columns: order_item_id (primary key), "
            "order_id (foreign key to orders.order_id), "
            "product_id (foreign key to products.product_id), "
            "quantity, unit_price, discount_pct. "
            "Each row represents a product line within an order. "
            "Use this table to calculate product sales and revenue."
        ),
    ),
    SchemaDocument(
        document_id="relationship_customer_orders",
        category="relationship",
        title="Customers and orders relationship",
        content=(
            "Join customers to orders using "
            "customers.customer_id = orders.customer_id. "
            "Use this relationship for customer order counts, "
            "customer sales, and customer revenue analysis."
        ),
    ),
    SchemaDocument(
        document_id="relationship_orders_items",
        category="relationship",
        title="Orders and order items relationship",
        content=(
            "Join orders to order_items using "
            "orders.order_id = order_items.order_id. "
            "Use this relationship to filter order lines by "
            "order date or order status."
        ),
    ),
    SchemaDocument(
        document_id="relationship_products_items",
        category="relationship",
        title="Products and order items relationship",
        content=(
            "Join products to order_items using "
            "products.product_id = order_items.product_id. "
            "Use this relationship for product and category "
            "sales analysis."
        ),
    ),
    SchemaDocument(
        document_id="rule_gross_line_value",
        category="business_rule",
        title="Gross line value",
        content=(
            "Gross line value is quantity * unit_price. "
            "This calculation excludes discounts."
        ),
    ),
    SchemaDocument(
        document_id="rule_net_line_value",
        category="business_rule",
        title="Net line value",
        content=(
            "Net line value is "
            "quantity * unit_price * (1 - discount_pct). "
            "Apply this formula when calculating net sales "
            "or net revenue."
        ),
    ),
    SchemaDocument(
        document_id="rule_recognized_revenue",
        category="business_rule",
        title="Recognized revenue",
        content=(
            "Recognized revenue includes net line value "
            "from completed orders only. "
            "Cancelled orders must be excluded from "
            "recognized revenue calculations. "
            "For cancelled-order reconciliation, calculate "
            "net line value using the same discount formula, "
            "but filter for cancelled orders."
        ),
    ),
    SchemaDocument(
        document_id="rule_date_ranges",
        category="business_rule",
        title="Date filtering",
        content=(
            "Date filters use an inclusive start date "
            "and an exclusive end date. "
            "For example, a calendar year from 2026 uses "
            "order_date >= DATE '2026-01-01' and "
            "order_date < DATE '2027-01-01'."
        ),
    ),
)


def get_schema_documents() -> tuple[SchemaDocument, ...]:
    """Return the curated schema knowledge corpus."""
    return SCHEMA_DOCUMENTS
