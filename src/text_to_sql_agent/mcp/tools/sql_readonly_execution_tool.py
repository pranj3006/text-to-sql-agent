import logging
from typing import Any, Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from text_to_sql_agent.app.text_to_sql import execute_sql


logger = logging.getLogger(__name__)


class SQLExecutionResponse(BaseModel):
    """Result of executing a read-only SQL query."""

    success: bool
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    error: str | None = None


def register_execution_tools(mcp: MCPServer) -> None:

    @mcp.tool()
    def execute_readonly_sql(
        sql: Annotated[
            str,
            Field(
                min_length=1,
                max_length=20_000,
                description="SQL query to validate and execute.",
            ),
        ],
    ) -> SQLExecutionResponse:
        """Validate and execute a read-only SQL query against the analytics database."""

        if not sql.strip():
            return SQLExecutionResponse(
                success=False,
                error="SQL query cannot be empty or whitespace only.",
            )

        try:
            result = execute_sql(sql.strip())

            return SQLExecutionResponse(
                success=True,
                sql=result["sql"],
                columns=result["columns"],
                rows=result["rows"],
                row_count=result["row_count"],
            )

        except ValueError as exc:
            # Includes SQL validation failures.
            return SQLExecutionResponse(
                success=False,
                error=str(exc),
            )

        except SQLAlchemyError:
            logger.exception("SQL execution failed.")
            return SQLExecutionResponse(
                success=False,
                error="SQL execution failed. Check server logs for details.",
            )

        except Exception:
            logger.exception("Unexpected error during SQL execution.")
            return SQLExecutionResponse(
                success=False,
                error="An unexpected error occurred during SQL execution.",
            )