"""
Criação de registros lógicos de páginas do PDF.
Não gera imagens, não executa OCR e não classifica páginas.
"""
from __future__ import annotations

import uuid

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.file_page import FilePage, FilePageInitialStatus
from app.services.storage_service import get_storage_service


class FilePageService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._storage = get_storage_service()

    def create_pages_for_file(self, file_id: str) -> list[FilePage]:
        document = self._session.execute(
            select(Document).where(Document.id == file_id)
        ).scalar_one_or_none()
        if not document:
            raise ValueError("Arquivo não encontrado.")

        stream, _ = self._storage.download_to_stream(
            document.storage_key,
            bucket=document.storage_bucket,
        )
        pdf_bytes = stream.read()

        created_or_updated: list[FilePage] = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
            for index, page in enumerate(pdf, start=1):
                rect = page.rect
                file_page = self._session.execute(
                    select(FilePage).where(
                        FilePage.file_id == file_id,
                        FilePage.page_number == index,
                    )
                ).scalar_one_or_none()
                if not file_page:
                    file_page = FilePage(
                        id=str(uuid.uuid4()),
                        file_id=file_id,
                        page_number=index,
                    )
                    self._session.add(file_page)

                file_page.width = float(rect.width)
                file_page.height = float(rect.height)
                file_page.status_ocr = FilePageInitialStatus.PENDING.value
                file_page.status_preview = FilePageInitialStatus.PENDING.value
                created_or_updated.append(file_page)

        self._session.flush()
        return created_or_updated
