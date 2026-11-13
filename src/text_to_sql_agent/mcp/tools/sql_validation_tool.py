from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from text_to_sql_agent.app.text_to_sql import validate_sql

# Configure these using your existing database/schema configuration.
ALLOWED_TABLES = frozenset({
    "customers",
    "products",
    "orders",
    "order_items",
})

TARGET_SCHEMA = "public"
TARGET_CATALOG = None

class SQLValidationResponse(BaseModel):
    """Result of SQL validation."""

    valid: bool
    normalized_sql: str | None = None
    error: str | None = None


def register_sql_tools(mcp: MCPServer) -> None:

    @mcp.tool()
    def validate_sql_tool(
        sql: Annotated[
            str,
            Field(
                min_length=1,
                max_length=20_000,
                description="SQL query to validate.",
            ),
        ],
    ) -> SQLValidationResponse:
        """Validate and normalize a read-only SQL query."""

        if not sql.strip():
            return SQLValidationResponse(
                valid=False,
                error="SQL query cannot be empty or whitespace only.",
            )

        try:
            normalized_sql = validate_sql(
                sql.strip(),
                dialect="postgres",
                allowed_tables=ALLOWED_TABLES,
                schema=TARGET_SCHEMA,
                catalog=TARGET_CATALOG,
            )

            return SQLValidationResponse(
                valid=True,
                normalized_sql=normalized_sql,
            )

        except ValueError as exc:
            return SQLValidationResponse(
                valid=False,
                error=str(exc),
            )