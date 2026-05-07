"""
Tarefas Celery para pipeline de OCR.
Processa PDFs grandes em chunks de páginas para evitar timeout.
"""
from __future__ import annotations

import io
import logging
import uuid
from typing import Optional

from celery import shared_task
from sqlalchemy import select

from app.tasks.celery_app import celery_app

logger = logging.getLogger("officejoe.tasks.ocr")


def _get_sync_session():
    """Sessão síncrona para uso no Celery (não async)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import get_settings

    settings = get_settings()
    # Converte URL asyncpg -> psycopg2 para uso síncrono no Celery
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url, pool_pre_ping=True)
    Session = sessionmaker(engine)
    return Session()


@celery_app.task(
    bind=True,
    name="app.tasks.ocr_tasks.run_ocr_pipeline",
    max_retries=3,
    default_retry_delay=60,
    queue="ocr",
)
def run_ocr_pipeline(self, document_id: str) -> dict:
    """
    Pipeline completo de OCR para um documento:
    1. Baixa o PDF do MinIO (sem modificar o original)
    2. Processa em chunks de OCR_MAX_PAGES_PER_TASK páginas
    3. Persiste PageResult por página
    4. Enfileira extração estruturada
    5. Enfileira geração de embeddings
    """
    from app.db.models.document import Document, DocumentStatus
    from app.db.models.page import Page
    from app.services.storage_service import get_storage_service
    from app.services.ocr_service import get_ocr_service
    from app.core.config import get_settings
    from app.core.audit import AuditAction, log_audit

    settings = get_settings()
    session = _get_sync_session()

    try:
        doc = session.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if not doc:
            logger.error("Documento não encontrado: %s", document_id)
            return {"status": "error", "detail": "Documento não encontrado"}

        # Atualiza status
        doc.status = DocumentStatus.OCR_RUNNING.value
        doc.ocr_task_id = self.request.id
        session.commit()

        logger.info("Iniciando OCR: doc=%s task=%s", document_id, self.request.id)

        # Baixa PDF do MinIO
        storage = get_storage_service()
        stream, file_size = storage.download_to_stream(doc.storage_key)
        pdf_bytes = stream.read()

        # Processa com OCR service
        ocr_service = get_ocr_service()
        result = ocr_service.process_document_bytes(pdf_bytes, document_id)

        if result.error and not result.pages:
            doc.status = DocumentStatus.OCR_FAILED.value
            doc.error_message = result.error
            session.commit()
            log_audit(
                action=AuditAction.OCR_FAILED,
                resource_type="document",
                resource_id=document_id,
                details={"error": result.error},
                success=False,
            )
            return {"status": "error", "detail": result.error}

        # Persiste páginas
        doc.total_pages = result.total_pages
        doc.ocr_engine_used = result.engine_used
        doc.ocr_avg_confidence = f"{result.avg_confidence:.3f}"

        pages_created = 0
        for page_result in result.pages:
            existing = session.execute(
                select(Page).where(
                    Page.document_id == document_id,
                    Page.page_number == page_result.page_number,
                )
            ).scalar_one_or_none()

            page_obj = existing or Page(id=str(uuid.uuid4()), document_id=document_id)
            page_obj.page_number = page_result.page_number
            page_obj.raw_text = page_result.raw_text
            page_obj.text_length = len(page_result.raw_text or "")
            page_obj.ocr_engine = page_result.ocr_engine
            page_obj.ocr_confidence = page_result.confidence
            page_obj.has_text_layer = page_result.has_text_layer
            page_obj.is_image_only = page_result.is_image_only
            page_obj.width_pt = page_result.width_pt
            page_obj.height_pt = page_result.height_pt
            page_obj.text_blocks = page_result.text_blocks
            page_obj.tables_detected = page_result.tables

            if not existing:
                session.add(page_obj)
            pages_created += 1

        doc.status = DocumentStatus.OCR_COMPLETED.value
        session.commit()

        log_audit(
            action=AuditAction.OCR_COMPLETED,
            resource_type="document",
            resource_id=document_id,
            details={
                "total_pages": result.total_pages,
                "avg_confidence": result.avg_confidence,
                "engine": result.engine_used,
                "pages_created": pages_created,
            },
        )

        # Enfileira próximo estágio
        from app.tasks.extraction_tasks import run_extraction_pipeline
        from app.tasks.embedding_tasks import run_embedding_pipeline

        run_extraction_pipeline.apply_async(args=[document_id], queue="extraction", countdown=5)
        run_embedding_pipeline.apply_async(args=[document_id], queue="embeddings", countdown=30)

        logger.info(
            "OCR concluído: doc=%s pages=%d conf=%.3f",
            document_id, result.total_pages, result.avg_confidence,
        )
        return {
            "status": "completed",
            "document_id": document_id,
            "total_pages": result.total_pages,
            "avg_confidence": result.avg_confidence,
            "engine": result.engine_used,
        }

    except Exception as exc:
        logger.exception("Erro no pipeline OCR: doc=%s", document_id)
        try:
            from app.db.models.document import DocumentStatus
            doc = session.execute(
                select(Document).where(Document.id == document_id)
            ).scalar_one_or_none()
            if doc:
                doc.status = DocumentStatus.OCR_FAILED.value
                doc.error_message = str(exc)
                session.commit()
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(
    name="app.tasks.ocr_tasks.retry_failed_documents",
    queue="ocr",
)
def retry_failed_documents() -> dict:
    """Re-enfileira documentos com OCR falhado (tarefa periódica)."""
    from app.db.models.document import Document, DocumentStatus

    session = _get_sync_session()
    try:
        failed_docs = session.execute(
            select(Document).where(Document.status == DocumentStatus.OCR_FAILED.value)
        ).scalars().all()

        requeued = 0
        for doc in failed_docs:
            logger.info("Re-enfileirando OCR para: %s", doc.id)
            run_ocr_pipeline.apply_async(args=[doc.id], queue="ocr")
            requeued += 1

        return {"requeued": requeued}
    finally:
        session.close()
