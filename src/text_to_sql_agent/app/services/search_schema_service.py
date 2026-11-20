
from text_to_sql_agent.app.rag.schema_documents import SchemaDocument
from text_to_sql_agent.mcp_app.mcp_client_module import MCPClient
from sqlalchemy import Engine
from text_to_sql_agent.app.core.config import settings

async def search_schema_tool_call(question: str,
    client: MCPClient,
    *,
    limit: int = 5,
    engine: Engine | None = None):

    search_schema_result = (
        await client.call_tool(
            "search_schema",
            {
                "query": question,
                "limit": limit,
            },
        )
    )
    is_error = getattr(search_schema_result, "isError", getattr(search_schema_result, "is_error", False))
    if is_error:
        error = search_schema_result.content[0].text            
        return {
            "question": question,
            "isError": True,
            "error": error,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }
        
    schema_results = search_schema_result.structured_content
    relevant_documents = [
        SchemaDocument(**document)
        for document in schema_results["documents"]
    ]    
    return {
            "question": question,
            "isError": False,
            "relevant_documents": relevant_documents    ,
            "model": settings.OPENAI_MODEL,
            "approach": "baseline_dynamic_schema",
        }