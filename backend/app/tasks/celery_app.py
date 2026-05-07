"""Configuração básica do Celery com Redis."""
from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "officejoe",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.processing_tasks",
    ],
)

# ── Configuração ──────────────────────────────────────────────────────────────

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,
    task_soft_time_limit=300,
    task_time_limit=600,
)

# ── Filas ─────────────────────────────────────────────────────────────────────

default_exchange = Exchange("default", type="direct")
processing_exchange = Exchange("processing", type="direct")

celery_app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("processing", processing_exchange, routing_key="processing"),
)
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

celery_app.conf.task_routes = {
    "app.tasks.processing_tasks.*": {"queue": "processing"},
}
