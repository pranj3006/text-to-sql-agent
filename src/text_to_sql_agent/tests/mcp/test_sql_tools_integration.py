import importlib
from collections.abc import Callable

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from text_to_sql_agent.app.core.config import settings


class DummyMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Callable] = {}

    def tool(self):
        def register(func):
            self.tools[func.__name__] = func
            return func

        return register


@pytest.fixture
def registered_sql_tools(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "TEXT_TO_SQL_SCHEMA", "public")
    engine = create_engine("sqlite://", poolclass=StaticPool)
    with engine.begin() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS public")
        connection.execute(
            text(
                "CREATE TABLE public.customers "
                "(customer_id INTEGER PRIMARY KEY, customer_name TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO public.customers VALUES "
                "(1, 'Alice'), (2, 'Bob')"
            )
        )

    import text_to_sql_agent.mcp_app.tools.sql_readonly_execution_tool as execution
    import text_to_sql_agent.mcp_app.tools.sql_validation_tool as validation
    import text_to_sql_agent.app.services.execute_sql_service as execute_sql_service

    importlib.reload(validation)
    importlib.reload(execution)
    monkeypatch.setattr(
        execution,
        "execute_sql",
        lambda sql: execute_sql_service.execute_sql(sql, engine=engine),
    )

    mcp = DummyMCP()
    validation.register_sql_tools(mcp)
    execution.register_execution_tools(mcp)

    yield mcp.tools

    engine.dispose()


def test_validation_and_execution_tools_work_together_with_database(
    registered_sql_tools,
):
    validate = registered_sql_tools["validate_sql_tool"]
    execute = registered_sql_tools["execute_readonly_sql"]

    validation_result = validate(
        "SELECT customer_name FROM customers ORDER BY customer_id"
    )

    assert validation_result.valid is True
    assert validation_result.normalized_sql == (
        'SELECT customer_name FROM "public".customers '
        "ORDER BY customer_id LIMIT 100"
    )

    execution_result = execute(validation_result.normalized_sql)

    assert execution_result.success is True
    assert execution_result.columns == ["customer_name"]
    assert execution_result.rows == [
        {"customer_name": "Alice"},
        {"customer_name": "Bob"},
    ]
    assert execution_result.row_count == 2
    assert execution_result.error is None


def test_validation_tool_rejection_does_not_execute_query(
    registered_sql_tools,
):
    validation_result = registered_sql_tools["validate_sql_tool"](
        "DELETE FROM customers"
    )

    assert validation_result.valid is False
    assert validation_result.normalized_sql is None
    assert validation_result.error == "Only read-only SELECT queries are allowed."
