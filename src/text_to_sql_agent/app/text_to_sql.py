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

MAX_ROWS = 100
STATEMENT_TIMEOUT_MS = 5_000

SYSTEM_PROMPT = """
You are a Text-to-SQL component for an analytics application.

Generate one read-only query that answers the user's question using only the
supplied schema and SQL dialect.

Rules:
1. Use only tables, views, and columns listed in the supplied schema.
2. Do not invent business definitions or schema objects.
3. Use explicit JOIN conditions and clear, concise output aliases.
4. Do not include identifiers or columns not needed to answer the question.
5. Use deterministic ordering for ranked results.
6. Return SQL only: no Markdown, code fences, or explanations.
"""

_query_engine: Engine | None = None
_query_engine_lock = threading.Lock()
_openai_client: OpenAI | None = None


@dataclass(frozen=True)
class SchemaContext:
    dialect: str
    schema: str
    description: str
    tables: frozenset[str]


def _sqlglot_dialect(dialect_name: str) -> str:
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
    global _openai_client

    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY must be configured to generate SQL.")
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def get_schema_context(engine: Engine) -> SchemaContext:
    """Reflect tables and views from the configured query database schema."""
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


def generate_sql(question: str, *, engine: Engine | None = None) -> str:
    """Generate SQL from the reflected schema of the configured query database."""
    query_engine = engine or get_query_database_engine()
    schema_context = get_schema_context(query_engine)
    response = _get_openai_client().responses.create(
        model=settings.OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=f"""
            {schema_context.description}

            USER QUESTION:
            {question}

            Return one read-only query in the supplied SQL dialect.
            """,
    )

    sql = response.output_text.strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    return re.sub(r"\s*```$", "", sql).strip()


def _apply_row_limit(tree: exp.Expression) -> None:
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
    """Allow one read-only query against reflected objects and cap its rows."""
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
    for function in tree.find_all(exp.Func):
        if function.sql_name().upper() in blocked_functions:
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
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def execute_sql(sql: str, *, engine: Engine | None = None) -> dict[str, Any]:
    """Execute a validated query through the external, read-only query engine."""
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


def answer_question(
    question: str, *, engine: Engine | None = None
) -> dict[str, Any]:
    """Run the dynamic-schema Text-to-SQL baseline."""
    query_engine = engine or get_query_database_engine()
    sql = generate_sql(question, engine=query_engine)
    result = execute_sql(sql, engine=query_engine)

    return {
        "question": question,
        **result,
        "model": settings.OPENAI_MODEL,
        "approach": "baseline_dynamic_schema",
    }
