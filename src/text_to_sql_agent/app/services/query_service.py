
from typing import Any
from sqlalchemy import Engine
from text_to_sql_agent.mcp_app.mcp_client_module import MCPClient
from text_to_sql_agent.app.services.validate_sql_service import validate_sql_tool_call
from text_to_sql_agent.app.services.search_schema_service import search_schema_tool_call
from text_to_sql_agent.app.services.execute_sql_service import execute_sql_tool_call
from text_to_sql_agent.app.services.generate_sql_service import generate_sql
from text_to_sql_agent.app.services import core_service as core

async def answer_query(
    question: str,
    client: MCPClient,
    *,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Retrieve context, validate generated SQL, execute it, and return evidence.

    MCP transport and tool-level failures are converted into the same stable
    error response shape so callers do not need to inspect provider details.
    """
    query_engine = engine or core.get_query_database_engine()

    search_schema_result = await search_schema_tool_call(
        question,
        limit=5,
        client=client,
        engine=query_engine,
    )

    if search_schema_result["isError"]:        
        return search_schema_result
    schema_results = search_schema_result

    relevant_documents = search_schema_result["relevant_documents"]

    sql = generate_sql(question, relevant_documents, engine=query_engine)

    validated_sql_result = await validate_sql_tool_call(sql, client=client)

    if validated_sql_result["isError"]:        
        return validated_sql_result

    validated_sql = validated_sql_result["validated_sql"]

    execution_result = await execute_sql_tool_call(
        validated_sql,
        client=client,
        question=question,
    )
    
    if execution_result["isError"]:
        return execution_result    
    return execution_result
