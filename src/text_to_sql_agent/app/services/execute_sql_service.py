from text_to_sql_agent.mcp_app.mcp_client_module import MCPClient
from text_to_sql_agent.app.core.config import settings
from typing import Any
from sqlalchemy import Engine
from text_to_sql_agent.app.services.validate_sql_service import validate_sql
from text_to_sql_agent.app.services import core_service as core

STATEMENT_TIMEOUT_MS = 5_000

def execute_sql(sql: str, *, engine: Engine | None = None) -> dict[str, Any]:
    """Validate and execute SQL with database-side and result-size controls.

    PostgreSQL uses a read-only transaction and statement timeout. SQLite
    enables query-only mode for the duration of the statement.
    """
    query_engine = engine or core.get_query_database_engine()
    schema_context = core.get_schema_context(query_engine)
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
                    {key: core.json_safe(value) for key, value in row.items()}
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

async def execute_sql_tool_call(validated_sql: str,
    client: MCPClient,
    *,
    question: str = "") -> dict[str, Any]:

    execution_result = await client.call_tool(
        "execute_readonly_sql",
        {
            "sql": validated_sql,
        },
    )    
    
    is_error = getattr(execution_result, "isError", getattr(execution_result, "is_error", False))
    if is_error:
        error = execution_result.content[0].text
        return {
            "question": question,
            "isError": True,
            "error": error,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }
    result = execution_result.structured_content
    return {
        "isError": False,
        "question": question,
        **result,
        "model": settings.OPENAI_MODEL,
        "approach": "baseline_dynamic_schema",
    }