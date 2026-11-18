from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

import text_to_sql_agent.app.main as main
from text_to_sql_agent.app.deps import get_mcp_client


class FakeMCPClient:
    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.startup_error: Exception | None = None

    async def __aenter__(self) -> "FakeMCPClient":
        if self.startup_error is not None:
            raise self.startup_error
        self.started = True
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        self.closed = True


@pytest.fixture
def lifecycle_mocks(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    client = FakeMCPClient()
    ensure_pgvector_extension = AsyncMock()
    dispose_query_database_engine = Mock()
    dispose_app_database_engine = AsyncMock()
    shutdown_otel = Mock()

    monkeypatch.setattr(main, "MCPClient", lambda _server_params: client)
    monkeypatch.setattr(
        main,
        "ensure_pgvector_extension",
        ensure_pgvector_extension,
    )
    monkeypatch.setattr(
        main,
        "dispose_query_database_engine",
        dispose_query_database_engine,
    )
    monkeypatch.setattr(
        type(main.engine),
        "dispose",
        dispose_app_database_engine,
    )
    monkeypatch.setattr(main, "shutdown_otel", shutdown_otel)

    return SimpleNamespace(
        client=client,
        ensure_pgvector_extension=ensure_pgvector_extension,
        dispose_query_database_engine=dispose_query_database_engine,
        dispose_app_database_engine=dispose_app_database_engine,
        shutdown_otel=shutdown_otel,
    )


@pytest.mark.asyncio
async def test_startup_starts_mcp_client_and_exposes_app_state(
    lifecycle_mocks: SimpleNamespace,
):
    async with main.app.router.lifespan_context(main.app):
        assert lifecycle_mocks.client.started is True
        assert main.app.state.mcp_client is lifecycle_mocks.client
        assert get_mcp_client(SimpleNamespace(app=main.app)) is lifecycle_mocks.client

    lifecycle_mocks.ensure_pgvector_extension.assert_awaited_once_with(main.engine)


@pytest.mark.asyncio
async def test_shutdown_closes_mcp_client_and_disposes_resources(
    lifecycle_mocks: SimpleNamespace,
):
    async with main.app.router.lifespan_context(main.app):
        pass

    assert lifecycle_mocks.client.closed is True
    assert main.app.state.mcp_client is None
    lifecycle_mocks.dispose_query_database_engine.assert_called_once_with()
    lifecycle_mocks.dispose_app_database_engine.assert_awaited_once_with()
    lifecycle_mocks.shutdown_otel.assert_called_once_with()


def test_mcp_startup_failure_fails_application_startup_cleanly(
    lifecycle_mocks: SimpleNamespace,
):
    lifecycle_mocks.client.startup_error = RuntimeError("MCP startup failed")

    with pytest.raises(RuntimeError, match="MCP startup failed"):
        with TestClient(main.app):
            pytest.fail("Application startup unexpectedly succeeded")

    assert main.app.state.mcp_client is None
    lifecycle_mocks.dispose_query_database_engine.assert_called_once_with()
    lifecycle_mocks.dispose_app_database_engine.assert_awaited_once_with()
    lifecycle_mocks.shutdown_otel.assert_called_once_with()
