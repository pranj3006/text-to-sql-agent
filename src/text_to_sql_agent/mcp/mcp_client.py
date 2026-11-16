import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from text_to_sql_agent.mcp.mcp_client_module import MCPClient, MCPConnectionError

async def main() -> None:
    server_params = StdioServerParameters(
        command="uv",
        args=["run","python", "mcp/mcp_server.py"],
    )

    async with MCPClient(server_params) as client:
            tools = await client.list_tools()

            for tool in tools:
                print(tool)

            ### Test search_schema tool
            result = await client.call_tool(
                "search_schema",
                {
                    "query": "net revenue by product category",
                    "limit": 5,
                },
            )

            if result.is_error:
                raise RuntimeError("search_schema MCP tool execution failed")

            schema_result = result.structured_content

            documents = schema_result["documents"]
            count = schema_result["count"]
            print(f"Found {count} documents matching the query.")

            ### Test validate_sql_tool tool
            result = await client.call_tool(
                "validate_sql_tool",
                {
                    "sql": "Select * from customers",                    
                },
            )

            if result.is_error:
                raise RuntimeError("validate_sql_toolMCP tool execution failed")

            schema_result = result.structured_content

            valid = schema_result["valid"]
            normalized_sql = schema_result["normalized_sql"]
            print(f"SQL is valid: {valid}")

            ### Test execute_readonly_sql tool
            result = await client.call_tool(
                "execute_readonly_sql",
                {
                    "sql": normalized_sql,                    
                },
            )

            if result.is_error:
                raise RuntimeError("execute_readonly_sql MCP tool execution failed")

            schema_result = result.structured_content            
            count = schema_result["row_count"]
            print(f"SQL execution returned {count} rows.")

if __name__ == "__main__":
    asyncio.run(main())