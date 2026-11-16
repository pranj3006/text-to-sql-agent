from fastapi import Request
from text_to_sql_agent.mcp_app.mcp_client_module import MCPClient, MCPConnectionError


def get_mcp_client(request: Request) -> MCPClient:
    client = getattr(request.app.state, "mcp_client", None)

    if client is None:
        raise MCPConnectionError("MCP client is unavailable.")

    return client