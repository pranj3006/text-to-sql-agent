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
)