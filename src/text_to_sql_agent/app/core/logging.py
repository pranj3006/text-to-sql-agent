"""
Structured logging setup.

Design:
- All logs are JSON (via python-json-logger) so they're OTel/App-Insights
  ready the moment OTEL_EXPORTER flips from 'console' to 'otlp'.
- Logs go to stdout (for container log collection) AND to a rotating
  file under LOG_DIR (for local/back-reference debugging).
- A `correlation_id` contextvar is threaded through every request via
  RequestContextMiddleware so all logs for one request can be grepped
  together, and every log line carries trace_id/span_id once OTel is on.
"""
import logging
import logging.handlers
import os
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

from text_to_sql_agent.app.core.config import settings

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")


class ContextFilter(logging.Filter):
    """Injects correlation_id / user_id / trace context into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get()
        record.user_id = user_id_ctx.get()

        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                record.trace_id = format(ctx.trace_id, "032x")
                record.span_id = format(ctx.span_id, "016x")
            else:
                record.trace_id = "-"
                record.span_id = "-"
        except Exception:
            record.trace_id = "-"
            record.span_id = "-"
        return True


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    root.handlers.clear()

    fmt_fields = "%(asctime)s %(levelname)s %(name)s %(message)s " \
                 "%(correlation_id)s %(user_id)s %(trace_id)s %(span_id)s"

    if settings.LOG_JSON:
        formatter = jsonlogger.JsonFormatter(fmt_fields, rename_fields={
            "asctime": "timestamp", "levelname": "level", "name": "logger",
        })
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | corr=%(correlation_id)s "
            "user=%(user_id)s trace=%(trace_id)s | %(message)s"
        )

    context_filter = ContextFilter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(context_filter)
    root.addHandler(stream_handler)

    os.makedirs(settings.LOG_DIR, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(settings.LOG_DIR, f"{settings.APP_NAME}.log"),
        maxBytes=50 * 1024 * 1024,
        backupCount=10,
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)
    root.addHandler(file_handler)

    # Quiet down noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "azure"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
