"""
Configuração do Celery com filas separadas por tipo de tarefa.
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "officejoe",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.ocr_tasks",
        "app.tasks.extraction_tasks",
        "app.tasks.embedding_tasks",
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
    worker_prefetch_multiplier=1,  # Um task por vez para OCR pesado
    result_expires=86400 * 7,      # Resultados expiram em 7 dias
    task_soft_time_limit=3600,     # 1h soft limit
    task_time_limit=7200,          # 2h hard limit
)

# ── Filas ─────────────────────────────────────────────────────────────────────

default_exchange = Exchange("default", type="direct")
ocr_exchange = Exchange("ocr", type="direct")
extraction_exchange = Exchange("extraction", type="direct")
embeddings_exchange = Exchange("embeddings", type="direct")

celery_app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("ocr", ocr_exchange, routing_key="ocr"),
    Queue("extraction", extraction_exchange, routing_key="extraction"),
    Queue("embeddings", embeddings_exchange, routing_key="embeddings"),
)
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

celery_app.conf.task_routes = {
    "app.tasks.ocr_tasks.*": {"queue": "ocr"},
    "app.tasks.extraction_tasks.*": {"queue": "extraction"},
    "app.tasks.embedding_tasks.*": {"queue": "embeddings"},
}

# ── Tarefas periódicas ────────────────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    "reprocess-failed-ocr": {
        "task": "app.tasks.ocr_tasks.retry_failed_documents",
        "schedule": crontab(hour="*/6"),  # A cada 6 horas
    },
}
