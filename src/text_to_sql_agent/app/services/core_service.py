

import threading
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from openai import OpenAI
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.engine import make_url
from sqlglot import exp

from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument

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


def json_safe(value: Any) -> Any:
    """Convert database values that are not naturally JSON-serializable."""
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value