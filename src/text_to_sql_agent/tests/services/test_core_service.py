from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.services import core_service


@pytest.fixture
def sqlite_engine() -> Engine:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE customers "
                "(customer_id INTEGER PRIMARY KEY, customer_name TEXT)"
            )
        )
    yield engine
    engine.dispose()


def test_get_openai_client_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(core_service, "_openai_client", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        core_service._get_openai_client()


def test_get_openai_client_is_cached(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(core_service, "_openai_client", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    created: list[str] = []

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            created.append(api_key)

    monkeypatch.setattr(core_service, "OpenAI", FakeOpenAI)

    first = core_service._get_openai_client()
    second = core_service._get_openai_client()

    assert first is second
    assert created == ["test-key"]


def test_get_schema_context_reflects_database(sqlite_engine: Engine, monkeypatch):
    monkeypatch.setattr(settings, "TEXT_TO_SQL_SCHEMA", None)

    context = core_service.get_schema_context(sqlite_engine)

    assert context.dialect == "sqlite"
    assert context.schema == "main"
    assert context.tables == frozenset({"customers"})
    assert "customer_name TEXT" in context.description


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("12.50"), 12.5),
    ],
)
def test_json_safe_decimal(value, expected):
    assert core_service.json_safe(value) == expected
