from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClientError(Exception):
    """Base exception for MCP client errors."""


class MCPConnectionError(MCPClientError):
    """Raised when MCP connection or communication fails."""


class MCPToolError(MCPClientError):
    """Raised when an MCP tool reports an error."""


class MCPToolNotFoundError(MCPClientError):
    """Raised when the requested tool is unavailable."""


class MCPClient:

    def __init__(self, server_params: StdioServerParameters) -> None:
        self._server_params = server_params
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._available_tools: set[str] = set()

    async def start(self) -> None:
        """Start the MCP server subprocess and initialize the session."""

        if self._session is not None:
            return

        stack = AsyncExitStack()

        try:
            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(self._server_params)
            )

            session = ClientSession(read_stream, write_stream)

            await stack.enter_async_context(session)
            await session.initialize()

            tools = await session.list_tools()

            self._available_tools = {
                tool.name for tool in tools.tools
            }

            self._session = session
            self._exit_stack = stack

        except Exception as exc:
            await stack.aclose()
            raise MCPConnectionError(
                "Failed to initialize MCP client."
            ) from exc

    async def close(self) -> None:
        """Gracefully close the MCP session and server subprocess."""

        stack = self._exit_stack

        self._session = None
        self._exit_stack = None
        self._available_tools.clear()

        if stack is not None:
            await stack.aclose()

    async def list_tools(self) -> set[str]:
        """Return the tools discovered during initialization."""

        self._ensure_connected()
        return self._available_tools.copy()

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Invoke an MCP tool and return its result."""

        self._ensure_connected()

        if tool_name not in self._available_tools:
            raise MCPToolNotFoundError(
                f"MCP tool '{tool_name}' is not available."
            )

        try:
            result = await self._session.call_tool(
                tool_name,
                arguments,
            )

            if result.is_error:
                raise MCPToolError(
                    f"MCP tool '{tool_name}' execution failed: "
                    f"{self._extract_error(result)}"
                )

            return result

        except MCPToolError:
            raise

        except Exception as exc:
            raise MCPConnectionError(
                f"Communication failed while calling '{tool_name}'."
            ) from exc

    @staticmethod
    def _extract_error(result: Any) -> str:
        """Extract readable error information from an MCP result."""

        messages = [
            item.text
            for item in result.content
            if hasattr(item, "text")
        ]

        return "; ".join(messages) or "Unknown tool error."

    def _ensure_connected(self) -> None:
        if self._session is None:
            raise MCPConnectionError(
                "MCP client is not connected. Call start() first."
            )

    async def __aenter__(self) -> "MCPClient":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        await self.close()