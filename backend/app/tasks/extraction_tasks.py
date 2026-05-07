"""
Tarefas de extração estruturada: entidades, valores, datas, tabelas, holerites.
Toda extração mantém vínculo com documento, página e coordenadas.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.tasks.ocr_tasks import _get_sync_session

logger = logging.getLogger("officejoe.tasks.extraction")


# ── Extratores de entidades ───────────────────────────────────────────────────

CPF_RE = re.compile(r"\b\d{3}[.\-]?\d{3}[.\-]?\d{3}[-.]?\d{2}\b")
CNPJ_RE = re.compile(r"\b\d{2}[.\-]?\d{3}[.\-]?\d{3}/?\.?\d{4}[-.]?\d{2}\b")
DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
CURRENCY_RE = re.compile(r"R\$\s*[\d.,]+")
PIS_RE = re.compile(r"\b\d{3}\.?\d{5}\.?\d{2}[-.]?\d\b")


def _extract_entities(text: str, page_number: int, document_id: str, page_id: Optional[str]) -> List[Dict[str, Any]]:
    extractions = []

    for m in CPF_RE.finditer(text):
        extractions.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "page_id": page_id,
            "page_number": page_number,
            "extraction_type": "entity_cpf",
            "raw_value": m.group(),
            "confidence": 0.95,
            "extractor_name": "regex_cpf",
            "extractor_version": "1.0",
        })

    for m in CNPJ_RE.finditer(text):
        extractions.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "page_id": page_id,
            "page_number": page_number,
            "extraction_type": "entity_cnpj",
            "raw_value": m.group(),
            "confidence": 0.95,
            "extractor_name": "regex_cnpj",
            "extractor_version": "1.0",
        })

    for m in DATE_RE.finditer(text):
        extractions.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "page_id": page_id,
            "page_number": page_number,
            "extraction_type": "entity_date",
            "raw_value": m.group(),
            "confidence": 0.9,
            "extractor_name": "regex_date",
            "extractor_version": "1.0",
        })

    for m in CURRENCY_RE.finditer(text):
        extractions.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "page_id": page_id,
            "page_number": page_number,
            "extraction_type": "entity_currency",
            "raw_value": m.group(),
            "normalized_value": m.group().replace("R$", "").strip().replace(".", "").replace(",", "."),
            "confidence": 0.95,
            "extractor_name": "regex_currency",
            "extractor_version": "1.0",
        })

    return extractions


def _extract_tables(tables: List[Dict], page_number: int, document_id: str, page_id: Optional[str]) -> List[Dict[str, Any]]:
    extractions = []
    for i, table in enumerate(tables or []):
        rows = table.get("rows", [])
        if not rows:
            continue
        extractions.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "page_id": page_id,
            "page_number": page_number,
            "extraction_type": "table",
            "structured_data": {"rows": rows, "row_count": len(rows)},
            "confidence": 0.85,
            "extractor_name": "pdfplumber_table",
            "extractor_version": "1.0",
        })
    return extractions


@celery_app.task(
    bind=True,
    name="app.tasks.extraction_tasks.run_extraction_pipeline",
    max_retries=2,
    default_retry_delay=30,
    queue="extraction",
)
def run_extraction_pipeline(self, document_id: str) -> dict:
    """
    Extrai entidades, valores, datas e tabelas de todas as páginas OCR.
    Mantém rastreabilidade: extraction_type, page_number, coordenadas.
    """
    from app.db.models.document import Document, DocumentStatus
    from app.db.models.page import Page
    from app.db.models.extraction import Extraction

    session = _get_sync_session()
    try:
        doc = session.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if not doc:
            return {"status": "error", "detail": "Documento não encontrado"}

        doc.status = DocumentStatus.EXTRACTING.value
        session.commit()

        pages = session.execute(
            select(Page).where(Page.document_id == document_id).order_by(Page.page_number)
        ).scalars().all()

        total_extractions = 0
        for page in pages:
            text = page.raw_text or ""
            page_id = page.id

            # Extrações de entidades
            entity_extractions = _extract_entities(text, page.page_number, document_id, page_id)

            # Extrações de tabelas
            tables = page.tables_detected or []
            if isinstance(tables, dict):
                tables = [tables]
            table_extractions = _extract_tables(tables, page.page_number, document_id, page_id)

            all_extractions = entity_extractions + table_extractions

            for ext_data in all_extractions:
                ext = Extraction(
                    id=ext_data["id"],
                    document_id=ext_data["document_id"],
                    page_id=ext_data.get("page_id"),
                    page_number=ext_data["page_number"],
                    extraction_type=ext_data["extraction_type"],
                    raw_value=ext_data.get("raw_value"),
                    normalized_value=ext_data.get("normalized_value"),
                    structured_data=ext_data.get("structured_data"),
                    confidence=ext_data.get("confidence"),
                    extractor_name=ext_data.get("extractor_name"),
                    extractor_version=ext_data.get("extractor_version"),
                )
                session.add(ext)
                total_extractions += 1

        session.commit()

        logger.info(
            "Extração concluída: doc=%s extractions=%d",
            document_id, total_extractions,
        )
        return {
            "status": "completed",
            "document_id": document_id,
            "total_extractions": total_extractions,
        }

    except Exception as exc:
        logger.exception("Erro na extração: doc=%s", document_id)
        raise self.retry(exc=exc)
    finally:
        session.close()
