from text_to_sql_agent.app.core.config import settings
from sqlalchemy import Engine
from text_to_sql_agent.app.services import core_service as core

import re
from openai import OpenAI
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument
from text_to_sql_agent.app.services import core_service as core

# Baseline context: intentionally static.
# Later, RAG will retrieve only the relevant schema and business definitions.
BUSINESS_RULES = """
- Gross line value = quantity * unit_price.
- Net line value = quantity * unit_price * (1 - discount_pct).
- Recognized revenue includes net line value from completed orders only.
- Cancelled orders are excluded from recognized revenue.
- The net line value formula applies regardless of order status.
  For reconciliation questions about cancelled orders, calculate net
  line value using the discount formula and filter for cancelled orders.
- Date filters use an inclusive start date and an exclusive end date.
- Use consistent currency units.
"""

SCHEMA_CONTEXT_RULES = """
Use provided Schema Context stricly for understanding the database structure. 
Do not invent schema objects or relationships.
Do not add columns that are not needed to answer the question.
"""

RELEVANT_SCHEMA_DOCUMENTS_RULES = """
Use provided Relevant Schema Documents strictly for understanding relevance of question and relevant tables, columns and relationships.
"""

SYSTEM_PROMPT = """
You are a Text-to-SQL component for a retail analytics application.

Generate one PostgreSQL SELECT query that answers the user's question.

OUTPUT COLUMN NAMING
- Use concise, descriptive, and consistent output column aliases.
- For count metrics, use singular entity names where appropriate,
  such as completed_order_count.
- For calculated metrics, use consistent names such as net_revenue,
  gross_revenue, and net_line_value.
- For dimension columns, prefer the underlying business attribute name,
  such as category or customer_name, unless the question requests
  a more descriptive label.
- If the question explicitly specifies an output column name, use it.
- Do not add columns that are not needed to answer the question.
- Do not include primary keys or IDs unless explicitly requested.

Rules:
1. Use only tables and columns listed in the supplied schema.
2. Follow the business rules exactly.
3. Use explicit JOIN conditions.
4. Never generate data-changing statements or multiple statements.
5. Do not invent schema objects.
6. Return SQL only: no Markdown, code fences, or explanations.
7. Prefer clear aliases and deterministic ordering for ranked results.
8. For scalar SUM aggregations that must return a numeric total
   when no rows match, use COALESCE(SUM(...), 0).
9. When asked which entities have no qualifying records, prefer
   NOT EXISTS or an equivalent correct anti-join.
10. Return only the columns needed to answer the question.
    Do not include primary keys or other identifiers unless the
    question explicitly requests them.
11. Use the exact output aliases specified in the evaluation
    question or supplied output contract. If no alias is specified,
    use concise, descriptive aliases.
12. Do not add redundant columns for debugging or traceability.
13. For monthly aggregations, use a clear month column and a
    consistent date representation.
"""

def generate_sql(
    question: str,
    relevant_documents: list[SchemaDocument],
    *,
    engine: Engine | None = None,
) -> str:
    """Generate one SQL query for a question using reflected and retrieved context."""
    query_engine = engine or core.get_query_database_engine()
    schema_context = core.get_schema_context(query_engine)
    response = core._get_openai_client().responses.create(
        model=settings.OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=f"""
            SCHEMA CONTEXT RULES:
            {SCHEMA_CONTEXT_RULES}

            SCHEMA_CONTEXT:
            {schema_context.description}

            RELEVANT SCHEMA DOCUMENTS RULES:
            {RELEVANT_SCHEMA_DOCUMENTS_RULES}

            RELEVANT_SCHEMA_DOCUMENTS:
            {core.prepare_relevant_documents_instructions(relevant_documents)}

            BUSINESS RULES AND CONTEXT:
            {BUSINESS_RULES}

            USER QUESTION:
            {question}

            Return one read-only query in the supplied SQL dialect.
            """,
    )

    sql = response.output_text.strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    return re.sub(r"\s*```$", "", sql).strip()
