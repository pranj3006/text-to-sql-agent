import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.services.execute_sql_service import execute_sql


@pytest.fixture
def sqlite_engine(monkeypatch: pytest.MonkeyPatch) -> Engine:
    monkeypatch.setattr(settings, "TEXT_TO_SQL_SCHEMA", None)
    engine = create_engine("sqlite://", poolclass=StaticPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE customers "
                "(customer_id INTEGER PRIMARY KEY, customer_name TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO customers VALUES (1, 'Alice'), (2, 'Bob')"
            )
        )
    yield engine
    engine.dispose()


def test_execute_sql_returns_rows_with_sqlite_integration(sqlite_engine: Engine):
    result = execute_sql(
        "SELECT customer_name FROM customers ORDER BY customer_id",
        engine=sqlite_engine,
    )

    assert result["columns"] == ["customer_name"]
    assert result["rows"] == [
        {"customer_name": "Alice"},
        {"customer_name": "Bob"},
    ]
    assert result["row_count"] == 2
    assert "LIMIT 100" in result["sql"]
