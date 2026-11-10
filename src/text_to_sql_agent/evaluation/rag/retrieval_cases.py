
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RetrievalTestCase:
    case_id: str
    question: str
    retrieval_query: str
    relevance: Mapping[str, int]

    @property
    def expected_document_ids(self) -> frozenset[str]:
        """Return documents with a non-zero relevance grade."""
        return frozenset(
            document_id
            for document_id, grade in self.relevance.items()
            if grade > 0
        )


RETRIEVAL_TEST_CASES = (
    # ---------------------------------------------------------
    # Existing benchmark cases — unchanged
    # ---------------------------------------------------------

    RetrievalTestCase(
        case_id="R01",
        question="What is the total recognized revenue by product category?",
        retrieval_query=(
            "revenue OR product OR category OR order OR discount"
        ),
        relevance={
            "table_order_items": 2,
            "relationship_orders_items": 2,
            "rule_recognized_revenue": 2,
            "table_products": 2,
            "relationship_products_items": 2,
            "table_orders": 2,
            "rule_net_line_value": 2,
        },
    ),
    RetrievalTestCase(
        case_id="R02",
        question="What is the total number of orders by customer region?",
        retrieval_query="orders OR customers OR region OR customer",
        relevance={
            "relationship_customer_orders": 2,
            "table_customers": 2,
            "table_orders": 2,
        },
    ),
    RetrievalTestCase(
        case_id="R03",
        question="Show monthly recognized revenue trends.",
        retrieval_query=(
            "revenue OR monthly OR order OR sales OR discount"
        ),
        relevance={
            "relationship_orders_items": 2,
            "rule_recognized_revenue": 2,
            "table_order_items": 2,
            "table_orders": 2,
            "rule_net_line_value": 2,
            "rule_date_ranges": 1,
        },
    ),
    RetrievalTestCase(
        case_id="R04",
        question=(
            "Which five products generated the highest recognized revenue?"
        ),
        retrieval_query=(
            "revenue OR products OR product OR order OR discount"
        ),
        relevance={
            "table_order_items": 2,
            "relationship_orders_items": 2,
            "rule_recognized_revenue": 2,
            "relationship_products_items": 2,
            "table_orders": 2,
            "table_products": 2,
            "rule_net_line_value": 2,
        },
    ),
    RetrievalTestCase(
        case_id="R05",
        question=(
            "Compare gross and net revenue by product category."
        ),
        retrieval_query=(
            "revenue OR gross OR net OR product OR category "
            "OR discount OR completed OR orders OR status"
        ),
        relevance={
            "table_products": 2,
            "rule_net_line_value": 2,
            "rule_recognized_revenue": 2,
            "relationship_products_items": 2,
            "table_order_items": 2,
            "rule_gross_line_value": 2,
            "relationship_orders_items": 2,
            "table_orders": 2,
        },
    ),

    # ---------------------------------------------------------
    # New benchmark cases
    # ---------------------------------------------------------

    # Table identification: customer master data
    RetrievalTestCase(
        case_id="R06",
        question="How many customers belong to each region?",
        retrieval_query=(
            "customers OR customer OR region OR count"
        ),
        relevance={
            "table_customers": 2,
        },
    ),

    # Table identification + date filtering + order status
    RetrievalTestCase(
        case_id="R07",
        question="List cancelled orders placed during calendar year 2026.",
        retrieval_query=(
            "cancelled OR orders OR status OR order_date "
            "OR date OR 2026"
        ),
        relevance={
            "table_orders": 2,
            "rule_date_ranges": 2,
        },
    ),

    # Column-level schema retrieval
    RetrievalTestCase(
        case_id="R08",
        question=(
            "Which column stores the discount percentage for each "
            "order item?"
        ),
        retrieval_query=(
            "discount_pct OR discount OR percentage "
            "OR order_items OR columns"
        ),
        relevance={
            "table_order_items": 2,
        },
    ),

    # Gross calculation + product analysis
    RetrievalTestCase(
        case_id="R09",
        question="What is the gross sales amount for each product?",
        retrieval_query=(
            "gross OR sales OR quantity OR unit_price "
            "OR product OR products"
        ),
        relevance={
            "table_order_items": 2,
            "rule_gross_line_value": 2,
            "relationship_products_items": 2,
            "table_products": 2,
        },
    ),

    # Customer revenue analysis + net calculation + join discovery
    RetrievalTestCase(
        case_id="R10",
        question="What is the net sales amount for each customer?",
        retrieval_query=(
            "net OR sales OR revenue OR customer OR customers "
            "OR orders OR order_items OR discount"
        ),
        relevance={
            "table_customers": 2,
            "table_orders": 2,
            "table_order_items": 2,
            "relationship_customer_orders": 2,
            "relationship_orders_items": 2,
            "rule_net_line_value": 2,
        },
    ),

    # Date aggregation + order status
    RetrievalTestCase(
        case_id="R11",
        question="How many completed orders were placed in each month?",
        retrieval_query=(
            "completed OR orders OR monthly OR month "
            "OR order_date OR status"
        ),
        relevance={
            "table_orders": 2,
            "rule_date_ranges": 2,
        },
    ),

    # Cancelled-order reconciliation + gross/net calculations
    RetrievalTestCase(
        case_id="R12",
        question=(
            "Calculate gross and net line values for cancelled orders."
        ),
        retrieval_query=(
            "cancelled OR gross OR net OR line value "
            "OR discount OR quantity OR unit_price OR orders"
        ),
        relevance={
            "table_orders": 2,
            "table_order_items": 2,
            "relationship_orders_items": 2,
            "rule_recognized_revenue": 2,
            "rule_gross_line_value": 2,
            "rule_net_line_value": 2,
        },
    ),

    # Quantity aggregation + product category
    RetrievalTestCase(
        case_id="R13",
        question="How many units were sold in each product category?",
        retrieval_query=(
            "units OR quantity OR sold OR product "
            "OR category OR order_items"
        ),
        relevance={
            "table_order_items": 2,
            "table_products": 2,
            "relationship_products_items": 2,
        },
    ),

    # Multi-concept: customer region + order count + recognized net revenue
    RetrievalTestCase(
        case_id="R14",
        question=(
            "Show order counts and recognized net revenue "
            "for each customer region."
        ),
        retrieval_query=(
            "customer OR region OR orders OR count OR recognized "
            "OR net OR revenue OR completed OR discount"
        ),
        relevance={
            "table_customers": 2,
            "table_orders": 2,
            "table_order_items": 2,
            "relationship_customer_orders": 2,
            "relationship_orders_items": 2,
            "rule_recognized_revenue": 2,
            "rule_net_line_value": 2,
        },
    ),

    # Multi-concept: date range + category + gross/net + recognition
    RetrievalTestCase(
        case_id="R15",
        question=(
            "For completed orders placed during calendar year 2026, "
            "compare gross and net revenue by product category."
        ),
        retrieval_query=(
            "completed OR orders OR 2026 OR date OR gross OR net "
            "OR revenue OR product OR category OR discount"
        ),
        relevance={
            "table_orders": 2,
            "table_order_items": 2,
            "table_products": 2,
            "relationship_orders_items": 2,
            "relationship_products_items": 2,
            "rule_date_ranges": 2,
            "rule_recognized_revenue": 2,
            "rule_gross_line_value": 2,
            "rule_net_line_value": 2,
        },
    ),
)
