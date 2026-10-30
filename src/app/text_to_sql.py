
import os
import re
from decimal import Decimal
from typing import Any

import sqlglot
from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlglot import exp
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
DATABASE_URL = os.environ["DATABASE_URL"]
MAX_ROWS = 100

client = OpenAI()
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"options": "-c default_transaction_read_only=on"},
)

# Baseline context: intentionally static.
# Later, RAG will retrieve only the relevant schema and business definitions.
SCHEMA_CONTEXT = """
Database: app1_db
SQL dialect: PostgreSQL

Tables and columns:

customers(
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT,
    region TEXT
)

products(
    product_id INTEGER PRIMARY KEY,
    product_name TEXT,
    category TEXT
)

orders(
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers.customer_id,
    order_date DATE,
    status TEXT -- completed or cancelled
)

order_items(
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders.order_id,
    product_id INTEGER REFERENCES products.product_id,
    quantity INTEGER,
    unit_price NUMERIC,
    discount_pct NUMERIC -- decimal fraction, e.g. 0.10 means 10%
)

Relationships:
- orders.customer_id -> customers.customer_id
- order_items.order_id -> orders.order_id
- order_items.product_id -> products.product_id

Business rules:
- Gross line value = quantity * unit_price.
- Net line revenue = quantity * unit_price * (1 - discount_pct).
- Recognized revenue includes only orders with status = 'completed'.
- Cancelled orders must be excluded from recognized revenue.
- Date filters should use inclusive start and exclusive end boundaries.
- For average order value, calculate each completed order's net value first,
  then average the order totals.
- Currency is consistent across all records.
"""

SYSTEM_PROMPT = """
You are a Text-to-SQL component for a retail analytics application.

Generate one PostgreSQL SELECT query that answers the user's question.

Rules:
1. Use only tables and columns listed in the supplied schema.
2. Follow the business rules exactly.
3. Use explicit JOIN conditions.
4. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
   TRUNCATE, GRANT, REVOKE, or any other data-changing statement.
5. Do not invent schema objects.
6. Return SQL only: no Markdown, no code fences, and no explanation.
7. Prefer clear aliases and deterministic ordering for ranked results.
8. Use NULL-safe aggregation when appropriate.
"""


def generate_sql(question: str) -> str:
    """Generate SQL from a question using the static baseline context."""
    response = client.responses.create(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=f"""
            SCHEMA AND BUSINESS CONTEXT:
            {SCHEMA_CONTEXT}

            USER QUESTION:
            {question}

            Return only one PostgreSQL SELECT statement.
            """,
    )

    sql = response.output_text.strip()

    # Remove code fences if the model unexpectedly includes them.
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql).strip()

    return sql


def validate_sql(sql: str) -> str:
    """Allow one read-only SELECT query and cap its result size."""
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError as exc:
        raise ValueError("The generated SQL could not be parsed.") from exc

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Exactly one SQL statement is required.")

    tree = statements[0]

    # This baseline accepts SELECT statements, including SELECT with CTEs.
    # Set operations such as UNION are allowed too.
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise ValueError("Only read-only SELECT queries are allowed.")

    # Block potentially dangerous functions even inside a SELECT.
    blocked_functions = {
        "PG_SLEEP",
        "SET_CONFIG",
        "LO_IMPORT",
        "LO_EXPORT",
        "DBLINK",
        "DBLINK_EXEC",
    }
    for function in tree.find_all(exp.Func):
        if function.sql_name().upper() in blocked_functions:
            raise ValueError("The query contains a prohibited function.")

    # Apply a row limit if the model did not supply one.
    # This limits returned rows, not the amount of work the database performs.
    if tree.args.get("limit") is None:
        tree.set(
            "limit",
            exp.Limit(expression=exp.Literal.number(MAX_ROWS)),
        )

    return tree.sql(dialect="postgres")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def execute_sql(sql: str) -> dict[str, Any]:
    """Execute validated SQL using a read-only transaction."""
    safe_sql = validate_sql(sql)

    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout = '5000ms'"))
            result = connection.execute(text(safe_sql))
            rows = [
                {key: _json_safe(value) for key, value in row.items()}
                for row in result.mappings()
            ]

    return {
        "sql": safe_sql,
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
        "row_count": len(rows),
    }


def answer_question(question: str) -> dict[str, Any]:
    """End-to-end baseline pipeline."""
    sql = generate_sql(question)
    result = execute_sql(sql)

    return {
        "question": question,
        **result,
        "model": MODEL,
        "approach": "baseline_static_schema",
    }
