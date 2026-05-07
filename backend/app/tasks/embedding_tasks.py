"""
Tarefa Celery para geração de embeddings e indexação semântica.
Usa pgvector para busca por similaridade dentro dos documentos.
"""
from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from sqlalchemy import select, text

from app.tasks.celery_app import celery_app
from app.tasks.ocr_tasks import _get_sync_session

logger = logging.getLogger("officejoe.tasks.embedding")

CHUNK_SIZE = 1000       # chars por chunk
CHUNK_OVERLAP = 200     # overlap para contexto


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Divide texto em chunks com overlap para preservar contexto."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _get_embedding(text: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
    """Gera embedding via OpenAI. Retorna None se não configurado."""
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY não configurada. Embeddings desabilitados.")
            return None
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(input=text, model=model)
        return response.data[0].embedding
    except Exception as exc:
        logger.error("Falha ao gerar embedding: %s", exc)
        return None


@celery_app.task(
    bind=True,
    name="app.tasks.embedding_tasks.run_embedding_pipeline",
    max_retries=2,
    default_retry_delay=60,
    queue="embeddings",
)
def run_embedding_pipeline(self, document_id: str) -> dict:
    """
    Gera embeddings para todas as páginas do documento e persiste na tabela page_embeddings.
    """
    from app.db.models.document import Document, DocumentStatus
    from app.db.models.page import Page
    from app.core.config import get_settings

    settings = get_settings()
    session = _get_sync_session()

    try:
        doc = session.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if not doc:
            return {"status": "error", "detail": "Documento não encontrado"}

        pages = session.execute(
            select(Page).where(
                Page.document_id == document_id,
                Page.raw_text.isnot(None),
            ).order_by(Page.page_number)
        ).scalars().all()

        total_chunks = 0
        for page in pages:
            if not page.raw_text:
                continue

            chunks = _chunk_text(page.raw_text)
            for chunk_idx, chunk_text in enumerate(chunks):
                embedding = _get_embedding(chunk_text, settings.EMBEDDING_MODEL)

                embedding_id = str(uuid.uuid4())

                if embedding:
                    # Usa CAST explícito para evitar conflito com o bind marker `:embedding`
                    session.execute(
                        text("""
                            INSERT INTO page_embeddings
                                (id, page_id, document_id, case_id, chunk_index, chunk_text, embedding, model_name)
                            VALUES
                                (:id, :page_id, :document_id, :case_id, :chunk_index, :chunk_text, CAST(:embedding AS vector), :model_name)
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "id": embedding_id,
                            "page_id": page.id,
                            "document_id": document_id,
                            "case_id": doc.case_id,
                            "chunk_index": chunk_idx,
                            "chunk_text": chunk_text,
                            "embedding": str(embedding),
                            "model_name": settings.EMBEDDING_MODEL,
                        },
                    )
                else:
                    # Insere sem vetor (texto disponível para busca full-text)
                    session.execute(
                        text("""
                            INSERT INTO page_embeddings
                                (id, page_id, document_id, case_id, chunk_index, chunk_text, model_name)
                            VALUES
                                (:id, :page_id, :document_id, :case_id, :chunk_index, :chunk_text, :model_name)
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "id": embedding_id,
                            "page_id": page.id,
                            "document_id": document_id,
                            "case_id": doc.case_id,
                            "chunk_index": chunk_idx,
                            "chunk_text": chunk_text,
                            "model_name": "none",
                        },
                    )
                total_chunks += 1

        session.commit()

        # Atualiza status do documento
        doc.status = DocumentStatus.INDEXED.value
        doc.embedding_task_id = self.request.id
        session.commit()

        logger.info(
            "Embeddings gerados: doc=%s chunks=%d",
            document_id, total_chunks,
        )
        return {
            "status": "completed",
            "document_id": document_id,
            "total_chunks": total_chunks,
        }

    except Exception as exc:
        logger.exception("Erro no pipeline de embeddings: doc=%s", document_id)
        raise self.retry(exc=exc)
    finally:
        session.close()
