from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field

from text_to_sql_agent.app.rag.schema_retriever import (
    retrieve_schema_documents,
)


class SchemaDocumentResult(BaseModel):
    """A retrieved schema or business knowledge document."""

    document_id: str
    category: str
    title: str
    content: str


class SchemaSearchResponse(BaseModel):
    """Schema documents matching a natural-language query."""

    documents: list[SchemaDocumentResult]
    count: int

def register_search_schema_tools(mcp: MCPServer) -> None:

    @mcp.tool()
    async def search_schema(
        query: Annotated[
            str,
            Field(min_length=1, max_length=500, 
            description="Business question or schema search query."),
        ],
        limit: Annotated[
            int,
            Field(ge=1, le=10, description="Maximum number of documents to retrieve."),
        ] = 5,
    ) -> SchemaSearchResponse:
        """Search schema metadata and business rules using PostgreSQL full-text search."""

        if not query.strip():        
            # raise ValueError("Query cannot be empty or whitespace only.")
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text="Error: 'query' cannot be an empty string.")]
            )

        documents = await retrieve_schema_documents(
            query=query.strip(),
            limit=limit,
        )

        return SchemaSearchResponse(
            documents=[
                SchemaDocumentResult(
                    document_id=document.document_id,
                    category=document.category,
                    title=document.title,
                    content=document.content,
                )
                for document in documents
            ],
            count=len(documents),
        )
