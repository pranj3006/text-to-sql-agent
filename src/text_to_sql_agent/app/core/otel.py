"""
OpenTelemetry wiring. Two independent toggle points:

- OTEL_ENABLED=false     -> tracing skipped entirely (no exporter, no
  FastAPI/SQLAlchemy instrumentation attached). Use this for local
  debugging when the per-request console span dump is just noise you
  want out of the way - see README "Observability" for the one-line
  way to flip this without editing .env.
- OTEL_EXPORTER=console  -> traces printed to stdout (dev default, when enabled)
- OTEL_EXPORTER=otlp     -> traces shipped to OTEL_EXPORTER_OTLP_ENDPOINT
  (point this at the Azure Monitor OTLP ingestion endpoint / collector
  when App Insights integration is switched on - no code change needed
  elsewhere in the app).
"""
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from text_to_sql_agent.app.core.config import settings
from text_to_sql_agent.app.core.logging import get_logger

logger = get_logger(__name__)


def configure_otel(app: FastAPI, db_engine=None) -> None:
    if not settings.OTEL_ENABLED:
        logger.info("otel_disabled", extra={"reason": "OTEL_ENABLED=false"})
        return

    resource = Resource(attributes={SERVICE_NAME: settings.OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    if settings.OTEL_EXPORTER == "otlp" and settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    if db_engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=db_engine.sync_engine)


def get_tracer(name: str):
    return trace.get_tracer(name)
