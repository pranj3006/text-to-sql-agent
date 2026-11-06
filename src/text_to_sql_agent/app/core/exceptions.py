"""Domain exceptions + FastAPI exception handlers, registered once in main.py."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from text_to_sql_agent.app.core.logging import get_logger
from text_to_sql_agent.app.core.rbac import PermissionDenied

logger = get_logger(__name__)


class NotFoundError(Exception):
    def __init__(self, entity: str, identifier: str):
        self.entity, self.identifier = entity, identifier
        super().__init__(f"{entity} '{identifier}' not found")


class ConflictError(Exception):
    pass


class ExternalServiceError(Exception):
    """Raised when a downstream call (Azure OpenAI, MCP server, etc.) fails."""


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError):
        return JSONResponse(status.HTTP_404_NOT_FOUND, {"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def _conflict(request: Request, exc: ConflictError):
        return JSONResponse(status.HTTP_409_CONFLICT, {"detail": str(exc)})

    @app.exception_handler(PermissionDenied)
    async def _forbidden(request: Request, exc: PermissionDenied):
        return JSONResponse(status.HTTP_403_FORBIDDEN, {"detail": str(exc) or "Permission denied"})

    @app.exception_handler(ExternalServiceError)
    async def _bad_gateway(request: Request, exc: ExternalServiceError):
        logger.error("external_service_error", extra={"error": str(exc)})
        return JSONResponse(status.HTTP_502_BAD_GATEWAY, {"detail": "Upstream service error"})

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled_exception")
        return JSONResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR, {"detail": "Internal server error"}
        )
