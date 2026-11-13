from typing import Annotated
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field
from text_to_sql_agent.mcp.tools.search_schema_tool import register_search_schema_tools
from text_to_sql_agent.mcp.tools.sql_validation_tool import register_sql_tools
from text_to_sql_agent.mcp.tools.sql_readonly_execution_tool import register_execution_tools

mcp = MCPServer("text-to-sql-mcp")

@mcp.tool()
def health_check() -> dict[str, str]:
    """Check whether the Text-to-SQL MCP server is running."""
    return {
        "status": "ok",
        "service": "text-to-sql-mcp",
    }

register_search_schema_tools(mcp)
register_sql_tools(mcp)
register_execution_tools(mcp)

if __name__ == "__main__":
    mcp.run()