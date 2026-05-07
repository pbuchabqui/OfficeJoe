"""
Tasks Celery básicas para processamento posterior de PDFs.
Não executa OCR, preview ou classificação.
"""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger("officejoe.tasks.processing")


def _get_sync_session():
    settings = get_settings()
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
    engine = create_engine(sync_url, pool_pre_ping=True)
    Session = sessionmaker(engine)
    return Session()


@celery_app.task(
    bind=True,
    name="app.tasks.processing_tasks.create_file_pages_job",
    queue="processing",
)
def create_file_pages_job(self, job_id: str) -> dict:
    """Cria registros lógicos de páginas e marca o job como completed."""
    from app.db.models.processing_job import ProcessingJob, ProcessingJobStatus
    from app.services.file_page_service import FilePageService

    session = _get_sync_session()
    try:
        job = session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        ).scalar_one_or_none()
        if not job:
            return {"status": "error", "detail": "Job não encontrado", "job_id": job_id}

        pages = FilePageService(session).create_pages_for_file(job.document_id)
        job.status = ProcessingJobStatus.COMPLETED.value
        job.celery_task_id = self.request.id
        job.result = {
            "message": "Registros lógicos de páginas criados.",
            "pages_created": len(pages),
        }
        session.commit()
        generate_page_previews_job.apply_async(args=[job.document_id], queue="processing")

        logger.info(
            "Páginas do arquivo registradas: job=%s file=%s pages=%d task=%s",
            job_id, job.document_id, len(pages), self.request.id,
        )
        return {"status": "completed", "job_id": job_id, "pages_created": len(pages)}
    except Exception as exc:
        session.rollback()
        try:
            job = session.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            ).scalar_one_or_none()
            if job:
                job.status = ProcessingJobStatus.FAILED.value
                job.error_message = str(exc)
                session.commit()
        except Exception:
            session.rollback()
        logger.exception("Falha ao criar registros de páginas: job=%s", job_id)
        raise exc
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.processing_tasks.generate_page_previews_job",
    queue="processing",
)
def generate_page_previews_job(self, file_id: str, batch_size: int = 10) -> dict:
    """Gera previews PNG em batches para as páginas lógicas do arquivo."""
    from app.services.page_preview_service import PagePreviewService

    session = _get_sync_session()
    try:
        pages = PagePreviewService(session).generate_previews_for_file(
            file_id=file_id,
            batch_size=batch_size,
            image_format="png",
        )
        session.commit()
        run_basic_ocr_job.apply_async(args=[file_id], queue="processing")
        logger.info(
            "Previews gerados: file=%s pages=%d task=%s",
            file_id, len(pages), self.request.id,
        )
        return {"status": "completed", "file_id": file_id, "previews_created": len(pages)}
    except Exception as exc:
        session.rollback()
        logger.exception("Falha ao gerar previews: file=%s", file_id)
        raise exc
    finally:
        session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.processing_tasks.run_basic_ocr_job",
    queue="processing",
)
def run_basic_ocr_job(self, file_id: str, batch_size: int = 10) -> dict:
    """Executa OCR básico em batches para páginas lógicas."""
    from app.services.basic_ocr_service import BasicOCRService

    session = _get_sync_session()
    try:
        pages = BasicOCRService(session).process_file(file_id=file_id, batch_size=batch_size)
        session.commit()
        logger.info(
            "OCR básico concluído: file=%s pages=%d task=%s",
            file_id, len(pages), self.request.id,
        )
        return {"status": "completed", "file_id": file_id, "pages_processed": len(pages)}
    except Exception as exc:
        session.rollback()
        logger.exception("Falha no OCR básico: file=%s", file_id)
        raise exc
    finally:
        session.close()
