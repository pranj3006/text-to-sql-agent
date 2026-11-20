
import sys
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from mcp import StdioServerParameters
from pydantic import BaseModel, Field

from text_to_sql_agent.app.deps import get_mcp_client
from text_to_sql_agent.app.text_to_sql import (
    answer_question,
    dispose_query_database_engine,
)
from text_to_sql_agent.app.services.query_service import answer_query
from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.core.exceptions import register_exception_handlers
from text_to_sql_agent.app.core.logging import configure_logging, get_logger
from text_to_sql_agent.app.core.middleware.auth_middleware import AuthContextMiddleware
from text_to_sql_agent.app.core.middleware.logging_middleware import RequestContextMiddleware
from text_to_sql_agent.app.core.middleware.monitoring_middleware import MonitoringMiddleware, get_metrics_summary
from text_to_sql_agent.app.core.otel import configure_otel, shutdown_otel
from text_to_sql_agent.app.db.init_pgvector import ensure_pgvector_extension
from text_to_sql_agent.app.db.session import engine
from text_to_sql_agent.mcp_app.mcp_client_module import MCPClient

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", extra={"env": settings.APP_ENV})
    app.state.mcp_client = None

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "text_to_sql_agent.mcp_app.mcp_server"],
    )

    try:
        await ensure_pgvector_extension(engine)

        async with MCPClient(server_params) as mcp_client:
            app.state.mcp_client = mcp_client
            logger.info("mcp_client_started")

            yield
    except Exception:
        logger.exception("app_lifecycle_failure")
        raise
    finally:
        try:
            dispose_query_database_engine()
            await engine.dispose()
        finally:
            app.state.mcp_client = None
            shutdown_otel()
            logger.info("app_shutdown")

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,)


# --- Middleware stack (order matters: outermost added last runs first) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "local" else [],  # tighten per-env before prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MonitoringMiddleware)
app.add_middleware(AuthContextMiddleware)
app.add_middleware(RequestContextMiddleware)

register_exception_handlers(app)
configure_otel(app, db_engine=engine)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


router = APIRouter()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(request: QuestionRequest):
    try:
        return answer_question(request.question)
    except ValueError as exc:
        print("exc",exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Log the actual exception in a real application.
        print("exc",exc)
        raise HTTPException(
            status_code=500,
            detail="Unable to generate or execute the query.",
        ) from exc


@router.get("/mcp/tools")
async def get_mcp_tools(
    client: Annotated[MCPClient, Depends(get_mcp_client)],
):
    tools = await client.list_tools()

    return {
        "tools": sorted(tools),
        "count": len(tools),
    }


@router.get("/mcp/schema-search")
async def search_schema(
    client: Annotated[MCPClient, Depends(get_mcp_client)],
    query: str = Query(min_length=1, max_length=500),
):
    result = await client.call_tool(
        "search_schema",
        {
            "query": query,
            "limit": 5,
        },
    )

    return result.structured_content



@router.get("/mcp/query")
async def mcp_query(
    client: Annotated[MCPClient, Depends(get_mcp_client)],
    request: QuestionRequest
    ):
    try:
        result = await answer_query(
                    client=client,
                    question=request.question)
        return result.structured_content
    except ValueError as exc:
        print("exc",exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Log the actual exception in a real application.
        print("exc",exc)
        raise HTTPException(
            status_code=500,
            detail="Unable to generate or execute the query.",
        ) from exc


app.include_router(router)