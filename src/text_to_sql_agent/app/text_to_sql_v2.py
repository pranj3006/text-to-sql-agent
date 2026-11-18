import re
import threading
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import sqlglot
from openai import OpenAI
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.engine import make_url
from sqlglot import exp

from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument
from text_to_sql_agent.mcp_app.mcp_client_module import MCPClient

MAX_ROWS = 100
STATEMENT_TIMEOUT_MS = 5_000

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


_query_engine: Engine | None = None
_query_engine_lock = threading.Lock()
_openai_client: OpenAI | None = None


@dataclass(frozen=True)
class SchemaContext:
    """Reflected database metadata supplied to SQL generation and validation."""

    dialect: str
    schema: str
    description: str
    tables: frozenset[str]


def _sqlglot_dialect(dialect_name: str) -> str:
    """Map SQLAlchemy dialect names to the dialect names expected by SQLGlot."""
    return {
        "postgresql": "postgres",
        "mssql": "tsql",
        "mariadb": "mysql",
    }.get(dialect_name, dialect_name)


def get_query_database_engine() -> Engine:
    """Return the independently configured synchronous analytics engine."""
    global _query_engine

    if _query_engine is not None:
        return _query_engine

    with _query_engine_lock:
        if _query_engine is not None:
            return _query_engine

        database_url = settings.TEXT_TO_SQL_DATABASE_URL
        if not database_url:
            raise RuntimeError(
                "TEXT_TO_SQL_DATABASE_URL must be configured for Text-to-SQL queries."
            )

        url = make_url(database_url)
        if "+" in url.drivername and url.drivername.rsplit("+", 1)[1] in {
            "asyncpg",
            "aiosqlite",
            "asyncmy",
            "aiomysql",
        }:
            raise ValueError(
                "TEXT_TO_SQL_DATABASE_URL must use a synchronous SQLAlchemy driver."
            )

        _query_engine = create_engine(database_url, pool_pre_ping=True)
        return _query_engine


def dispose_query_database_engine() -> None:
    """Dispose the external query engine without affecting app persistence."""
    global _query_engine

    with _query_engine_lock:
        if _query_engine is not None:
            _query_engine.dispose()
            _query_engine = None


def _get_openai_client() -> OpenAI:
    """Return the process-local OpenAI client after validating API configuration."""
    global _openai_client

    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY must be configured to generate SQL.")
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def get_schema_context(engine: Engine) -> SchemaContext:
    """Reflect tables, views, columns, and foreign keys for SQL generation.

    The returned object is the allowlist source for execution validation:
    generated SQL may reference only objects present in ``tables``.
    """
    inspector = inspect(engine)
    schema = settings.TEXT_TO_SQL_SCHEMA or inspector.default_schema_name
    if not schema:
        raise ValueError(
            "Could not determine the query database schema; set TEXT_TO_SQL_SCHEMA."
        )

    table_names = inspector.get_table_names(schema=schema)
    view_names = inspector.get_view_names(schema=schema)
    object_names = sorted(set(table_names) | set(view_names))
    if not object_names:
        raise ValueError(f"No tables or views found in query schema {schema!r}.")

    details = [
        f"SQL dialect: {engine.dialect.name}",
        f"Schema: {schema}",
        "Tables and views:",
    ]
    for object_name in object_names:
        columns = inspector.get_columns(object_name, schema=schema)
        column_descriptions = [
            f"    {column['name']} {column['type']}"
            for column in columns
        ]
        details.append(f"{object_name}(\n" + ",\n".join(column_descriptions) + "\n)")

        if object_name in table_names:
            for foreign_key in inspector.get_foreign_keys(object_name, schema=schema):
                referred_schema = foreign_key.get("referred_schema") or schema
                details.append(
                    f"Relationship: {object_name}."
                    f"{', '.join(foreign_key['constrained_columns'])} -> "
                    f"{referred_schema}.{foreign_key['referred_table']}."
                    f"{', '.join(foreign_key['referred_columns'])}"
                )

    return SchemaContext(
        dialect=_sqlglot_dialect(engine.dialect.name),
        schema=schema,
        description="\n".join(details),
        tables=frozenset(object_names),
    )

def prepare_relevant_documents_instructions(relevant_documents: list[SchemaDocument]) -> str:
    """Format retrieved schema documents as bounded prompt context."""
    if not relevant_documents:
        return "None"

    instructions = []
    for doc in relevant_documents:
        instructions.append(
            f"Document: {doc.title}\n"
            f"Category: {doc.category}\n"
            f"Content:\n{doc.content}\n"
        )
    return "\n".join(instructions)

def generate_sql(
    question: str,
    relevant_documents: list[SchemaDocument],
    *,
    engine: Engine | None = None,
) -> str:
    """Generate one SQL query for a question using reflected and retrieved context."""
    query_engine = engine or get_query_database_engine()
    schema_context = get_schema_context(query_engine)
    response = _get_openai_client().responses.create(
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
            {prepare_relevant_documents_instructions(relevant_documents)}

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

def _apply_row_limit(tree: exp.Expression) -> None:
    """Preserve a smaller row limit or append the configured maximum limit."""
    # Capping here provides a deterministic resource limit even if model output
    # is valid SQL but omits or exceeds the application's row budget.
    limit = tree.args.get("limit")
    if limit is not None:
        expression = limit.expression
        if (
            isinstance(expression, exp.Literal)
            and expression.is_number
            and expression.this.isdecimal()
            and int(expression.this) <= MAX_ROWS
        ):
            return

    tree.set("limit", exp.Limit(expression=exp.Literal.number(MAX_ROWS)))


def validate_sql(
    sql: str,
    *,
    dialect: str = "postgres",
    allowed_tables: frozenset[str] | None = None,
    schema: str | None = None,
    catalog: str | None = None,
) -> str:
    """Parse, authorize, and normalize one read-only query.

    Raises ``ValueError`` when the SQL is malformed, changes data, calls a
    prohibited function, or references an object outside the supplied allowlist.
    """
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except sqlglot.errors.ParseError as exc:
        raise ValueError("The generated SQL could not be parsed.") from exc

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Exactly one SQL statement is required.")

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise ValueError("Only read-only SELECT queries are allowed.")

    blocked_functions = {
        "PG_SLEEP",
        "SET_CONFIG",
        "LO_IMPORT",
        "LO_EXPORT",
        "DBLINK",
        "DBLINK_EXEC",
    }
    # SQLGlot represents some dialect functions as anonymous function nodes,
    # so inspect both anonymous names and typed function names.
    for function in tree.find_all(exp.Func):
        function_name = (
            function.name if isinstance(function, exp.Anonymous) else function.sql_name()
        )
        if function_name.upper() in blocked_functions:
            raise ValueError("The query contains a prohibited function.")

    if allowed_tables is not None:
        if schema is None:
            raise ValueError("A target schema is required for table allowlisting.")
        common_table_expressions = {
            cte.alias_or_name for cte in tree.find_all(exp.CTE)
        }
        for table in tree.find_all(exp.Table):
            if (
                table.name in common_table_expressions
                and not table.db
                and not table.catalog
            ):
                continue
            if table.name not in allowed_tables:
                raise ValueError(
                    f"The query references an unavailable table or view: {table.name}."
                )
            if table.db and (schema is None or table.db != schema):
                raise ValueError("The query references an unavailable schema.")
            if table.catalog and (catalog is None or table.catalog != catalog):
                raise ValueError("The query references an unavailable database.")
            if not table.db:
                table.set("db", exp.to_identifier(schema, quoted=True))

    _apply_row_limit(tree)
    return tree.sql(dialect=dialect)


def _json_safe(value: Any) -> Any:
    """Convert database values that are not naturally JSON-serializable."""
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def execute_sql(sql: str, *, engine: Engine | None = None) -> dict[str, Any]:
    """Validate and execute SQL with database-side and result-size controls.

    PostgreSQL uses a read-only transaction and statement timeout. SQLite
    enables query-only mode for the duration of the statement.
    """
    query_engine = engine or get_query_database_engine()
    schema_context = get_schema_context(query_engine)
    safe_sql = validate_sql(
        sql,
        dialect=schema_context.dialect,
        allowed_tables=schema_context.tables,
        schema=schema_context.schema,
        catalog=query_engine.url.database,
    )

    with query_engine.connect() as connection:
        try:
            with connection.begin():
                if query_engine.dialect.name == "postgresql":
                    connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                    connection.exec_driver_sql(
                        f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT_MS}ms'"
                    )
                elif query_engine.dialect.name == "sqlite":
                    connection.exec_driver_sql("PRAGMA query_only = ON")

                result = connection.exec_driver_sql(safe_sql)
                rows = [
                    {key: _json_safe(value) for key, value in row.items()}
                    for row in result.mappings()
                ]
        finally:
            if query_engine.dialect.name == "sqlite":
                connection.exec_driver_sql("PRAGMA query_only = OFF")

    return {
        "sql": safe_sql,
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
        "row_count": len(rows),
    }


async def answer_question(
    question: str,
    client: MCPClient,
    *,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Retrieve context, validate generated SQL, execute it, and return evidence.

    MCP transport and tool-level failures are converted into the same stable
    error response shape so callers do not need to inspect provider details.
    """
    query_engine = engine or get_query_database_engine()

    search_schema_result = (
        await client.call_tool(
            "search_schema",
            {
                "query": question,
                "limit": 5,
            },
        )
    )
    if search_schema_result.isError:
        error = search_schema_result.content[0].text            
        return {
            "question": question,
            "error": error,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }
        
    schema_results = search_schema_result.structured_content
    relevant_documents = [
        SchemaDocument(**document)
        for document in schema_results["documents"]
    ]

    sql = generate_sql(question, relevant_documents, engine=query_engine)

    validated_sql_result = await client.call_tool(
        "validate_sql_tool",
        {
            "sql": sql,            
        },
    )
    if validated_sql_result.isError:
        error = validated_sql_result.content[0].text
        return {
            "question": question,
            "error": error,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }
    else:
        validation_result = validated_sql_result.structured_content  
        if not validation_result["valid"]:
            error = validation_result["error"]
            return {
            "question": question,
            "error": error,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }

    validation_result = validated_sql_result.structured_content    
    
    validated_sql = validation_result["normalized_sql"]

    execution_result = await client.call_tool(
        "execute_readonly_sql",
        {
            "sql": validated_sql,            
        },
    )    
    
    if execution_result.isError:
        error =execution_result.content[0].text
        return {
            "question": question,
            "error": error,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }
    result = execution_result.structured_content
    return {
        "question": question,
        **result,
        "model": settings.OPENAI_MODEL,
        "approach": "baseline_dynamic_schema",
    }
