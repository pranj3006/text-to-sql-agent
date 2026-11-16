from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp import StdioServerParameters

import text_to_sql_agent.mcp_app.mcp_client_module as mcp_client_module
from text_to_sql_agent.mcp_app.mcp_client_module import (
    MCPClient,
    MCPConnectionError,
    MCPToolError,
    MCPToolNotFoundError,
)


@pytest.fixture
def client():
    return MCPClient(StdioServerParameters(command="unused"))


def install_fake_session(monkeypatch, tools=("health_check",)):
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.list_tools.return_value = SimpleNamespace(
        tools=[SimpleNamespace(name=name) for name in tools]
    )

    @asynccontextmanager
    async def fake_stdio_client(_server_params):
        yield object(), object()

    monkeypatch.setattr(mcp_client_module, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(
        mcp_client_module,
        "ClientSession",
        lambda _read_stream, _write_stream: session,
    )
    return session


@pytest.mark.asyncio
async def test_start_initializes_session_and_discovers_tools(client, monkeypatch):
    session = install_fake_session(monkeypatch, ("health_check", "search_schema"))

    await client.start()

    assert await client.list_tools() == {"health_check", "search_schema"}
    session.initialize.assert_awaited_once()
    session.list_tools.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_is_idempotent(client, monkeypatch):
    session = install_fake_session(monkeypatch)

    await client.start()
    await client.start()

    session.initialize.assert_awaited_once()
    session.list_tools.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_tools_returns_a_copy(client, monkeypatch):
    install_fake_session(monkeypatch, ("health_check",))
    await client.start()

    tools = await client.list_tools()
    tools.add("unregistered_tool")

    assert await client.list_tools() == {"health_check"}


@pytest.mark.asyncio
async def test_operations_require_a_started_client(client):
    with pytest.raises(MCPConnectionError, match="Call start\\(\\) first"):
        await client.list_tools()

    with pytest.raises(MCPConnectionError, match="Call start\\(\\) first"):
        await client.call_tool("health_check", {})


@pytest.mark.asyncio
async def test_start_failure_closes_resources_and_raises_connection_error(
    client, monkeypatch
):
    session = install_fake_session(monkeypatch)
    session.initialize.side_effect = RuntimeError("initialization failed")

    with pytest.raises(MCPConnectionError, match="Failed to initialize MCP client"):
        await client.start()

    session.__aexit__.assert_awaited_once()
    with pytest.raises(MCPConnectionError, match="Call start\\(\\) first"):
        await client.list_tools()


@pytest.mark.asyncio
async def test_server_startup_failure_raises_connection_error(client, monkeypatch):
    @asynccontextmanager
    async def failing_stdio_client(_server_params):
        raise RuntimeError("server failed to start")
        yield

    monkeypatch.setattr(
        mcp_client_module,
        "stdio_client",
        failing_stdio_client,
    )

    with pytest.raises(MCPConnectionError, match="Failed to initialize MCP client"):
        await client.start()

    with pytest.raises(MCPConnectionError, match="Call start\\(\\) first"):
        await client.list_tools()


@pytest.mark.asyncio
async def test_call_tool_returns_successful_result(client, monkeypatch):
    session = install_fake_session(monkeypatch)
    expected_result = SimpleNamespace(is_error=False)
    session.call_tool.return_value = expected_result
    await client.start()

    result = await client.call_tool("health_check", {"verbose": True})

    assert result is expected_result
    session.call_tool.assert_awaited_once_with("health_check", {"verbose": True})


@pytest.mark.asyncio
async def test_call_tool_rejects_unknown_tool(client, monkeypatch):
    session = install_fake_session(monkeypatch)
    await client.start()

    with pytest.raises(MCPToolNotFoundError, match="not available"):
        await client.call_tool("missing_tool", {})

    session.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_call_tool_converts_tool_error_with_readable_message(client, monkeypatch):
    session = install_fake_session(monkeypatch)
    session.call_tool.return_value = SimpleNamespace(
        is_error=True,
        content=[
            SimpleNamespace(text="validation rejected"),
            SimpleNamespace(type="image"),
        ],
    )
    await client.start()

    with pytest.raises(MCPToolError, match="validation rejected"):
        await client.call_tool("health_check", {})


@pytest.mark.asyncio
async def test_call_tool_uses_fallback_when_tool_error_has_no_text(
    client, monkeypatch
):
    session = install_fake_session(monkeypatch)
    session.call_tool.return_value = SimpleNamespace(is_error=True, content=[])
    await client.start()

    with pytest.raises(MCPToolError, match="Unknown tool error"):
        await client.call_tool("health_check", {})


@pytest.mark.asyncio
async def test_call_tool_wraps_communication_failure(client, monkeypatch):
    session = install_fake_session(monkeypatch)
    session.call_tool.side_effect = RuntimeError("transport failed")
    await client.start()

    with pytest.raises(MCPConnectionError, match="Communication failed"):
        await client.call_tool("health_check", {})


@pytest.mark.asyncio
async def test_close_clears_session_and_is_safe_to_repeat(client, monkeypatch):
    session = install_fake_session(monkeypatch)
    await client.start()

    await client.close()
    await client.close()

    session.__aexit__.assert_awaited_once()
    with pytest.raises(MCPConnectionError, match="Call start\\(\\) first"):
        await client.list_tools()


@pytest.mark.asyncio
async def test_async_context_manager_closes_client(client, monkeypatch):
    session = install_fake_session(monkeypatch)

    async with client as connected_client:
        assert connected_client is client
        assert await connected_client.list_tools() == {"health_check"}

    session.__aexit__.assert_awaited_once()
    with pytest.raises(MCPConnectionError, match="Call start\\(\\) first"):
        await client.list_tools()


@pytest.mark.asyncio
async def test_async_context_manager_closes_client_after_exception(
    client, monkeypatch
):
    session = install_fake_session(monkeypatch)
    body_error = RuntimeError("operation failed")

    with pytest.raises(RuntimeError, match="operation failed"):
        async with client:
            raise body_error

    session.__aexit__.assert_awaited_once()
    with pytest.raises(MCPConnectionError, match="Call start\\(\\) first"):
        await client.list_tools()


@pytest.mark.asyncio
async def test_client_can_restart_after_close(client, monkeypatch):
    sessions = []

    @asynccontextmanager
    async def fake_stdio_client(_server_params):
        yield object(), object()

    def fake_client_session(_read_stream, _write_stream):
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.list_tools.return_value = SimpleNamespace(
            tools=[SimpleNamespace(name="health_check")]
        )
        sessions.append(session)
        return session

    monkeypatch.setattr(mcp_client_module, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(
        mcp_client_module,
        "ClientSession",
        fake_client_session,
    )

    await client.start()
    await client.close()
    await client.start()

    assert await client.list_tools() == {"health_check"}
    assert len(sessions) == 2
    for session in sessions:
        session.initialize.assert_awaited_once()
        session.list_tools.assert_awaited_once()
    sessions[0].__aexit__.assert_awaited_once()

    await client.close()
    sessions[1].__aexit__.assert_awaited_once()
