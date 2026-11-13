import importlib
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def sql_readonly_execution_tool(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/app_db")
    monkeypatch.setenv("TEXT_TO_SQL_DATABASE_URL", "postgresql://localhost/analytics")

    import text_to_sql_agent.mcp.tools.sql_readonly_execution_tool as module

    importlib.reload(module)

    class DummyMCP:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(func):
                self.tools[func.__name__] = func
                return func

            return decorator

    mcp = DummyMCP()
    module.register_execution_tools(mcp)

    return module, mcp.tools["execute_readonly_sql"]


def test_execute_readonly_sql_executes_query(sql_readonly_execution_tool, monkeypatch):
    module, execute_readonly_sql = sql_readonly_execution_tool
    mock_execute_sql = MagicMock(
        return_value={
            "sql": "SELECT * FROM customers LIMIT 10",
            "columns": ["customer_id", "customer_name"],
            "rows": [{"customer_id": 1, "customer_name": "Alice"}],
            "row_count": 1,
        }
    )
    monkeypatch.setattr(module, "execute_sql", mock_execute_sql)

    response = execute_readonly_sql("  SELECT * FROM customers LIMIT 10  ")

    assert response.success is True
    assert response.sql == "SELECT * FROM customers LIMIT 10"
    assert response.columns == ["customer_id", "customer_name"]
    assert response.rows == [{"customer_id": 1, "customer_name": "Alice"}]
    assert response.row_count == 1
    assert response.error is None
    mock_execute_sql.assert_called_once_with("SELECT * FROM customers LIMIT 10")


def test_execute_readonly_sql_rejects_blank_sql(sql_readonly_execution_tool):
    module, execute_readonly_sql = sql_readonly_execution_tool
    module.execute_sql = MagicMock()

    response = execute_readonly_sql("   \n\t  ")

    assert response.success is False
    assert response.error == "SQL query cannot be empty or whitespace only."
    assert response.sql is None
    assert response.columns == []
    assert response.rows == []
    assert response.row_count == 0
    module.execute_sql.assert_not_called()


def test_execute_readonly_sql_returns_validation_error(sql_readonly_execution_tool, monkeypatch):
    module, execute_readonly_sql = sql_readonly_execution_tool
    mock_execute_sql = MagicMock(side_effect=ValueError("Unsafe query"))
    monkeypatch.setattr(module, "execute_sql", mock_execute_sql)

    response = execute_readonly_sql("SELECT pg_sleep(1)")

    assert response.success is False
    assert response.error == "Unsafe query"
    assert response.sql is None
    mock_execute_sql.assert_called_once_with("SELECT pg_sleep(1)")


def test_execute_readonly_sql_returns_db_error(sql_readonly_execution_tool, monkeypatch):
    module, execute_readonly_sql = sql_readonly_execution_tool
    mock_execute_sql = MagicMock(side_effect=SQLAlchemyError("database unavailable"))
    monkeypatch.setattr(module, "execute_sql", mock_execute_sql)

    response = execute_readonly_sql("SELECT * FROM customers")

    assert response.success is False
    assert response.error == "SQL execution failed. Check server logs for details."
    mock_execute_sql.assert_called_once_with("SELECT * FROM customers")


def test_execute_readonly_sql_returns_unexpected_error(sql_readonly_execution_tool, monkeypatch):
    module, execute_readonly_sql = sql_readonly_execution_tool
    mock_execute_sql = MagicMock(side_effect=RuntimeError("unexpected failure"))
    monkeypatch.setattr(module, "execute_sql", mock_execute_sql)

    response = execute_readonly_sql("SELECT * FROM customers")

    assert response.success is False
    assert response.error == "An unexpected error occurred during SQL execution."
    mock_execute_sql.assert_called_once_with("SELECT * FROM customers")
