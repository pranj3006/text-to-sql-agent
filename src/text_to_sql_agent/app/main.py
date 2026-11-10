
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from text_to_sql_agent.app.text_to_sql import (
    answer_question,
    dispose_query_database_engine,
)
from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.core.exceptions import register_exception_handlers
from text_to_sql_agent.app.core.logging import configure_logging, get_logger
from text_to_sql_agent.app.core.middleware.auth_middleware import AuthContextMiddleware
from text_to_sql_agent.app.core.middleware.logging_middleware import RequestContextMiddleware
from text_to_sql_agent.app.core.middleware.monitoring_middleware import MonitoringMiddleware, get_metrics_summary
from text_to_sql_agent.app.core.otel import configure_otel
from text_to_sql_agent.app.db.init_pgvector import ensure_pgvector_extension
from text_to_sql_agent.app.db.session import engine

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", extra={"env": settings.APP_ENV})
    try:
        await ensure_pgvector_extension(engine)
        yield
    finally:
        logger.info("app_shutdown")
        dispose_query_database_engine()
        await engine.dispose()

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
