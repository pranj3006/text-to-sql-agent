"""
Celery app instance. Redis DB1 = broker, DB2 = result backend (see config.py).
Run with:  celery -A app.core.celery_app.celery_app worker --loglevel=info
"""
from celery import Celery

from text_to_sql_agent.app.core.config import settings

celery_app = Celery(
    settings.APP_NAME,
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.agent_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 15,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
