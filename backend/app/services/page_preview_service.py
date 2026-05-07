"""
Geração de previews PNG para páginas lógicas de PDF.
Não executa OCR, marcação de coordenadas ou classificação.
"""
from __future__ import annotations

import io

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.file_page import FilePage, FilePageInitialStatus
from app.services.storage_service import get_storage_service


class PagePreviewService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._storage = get_storage_service()

    def generate_previews_for_file(
        self,
        file_id: str,
        batch_size: int = 10,
        image_format: str = "png",
    ) -> list[FilePage]:
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

        updated_pages: list[FilePage] = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
            offset = 0
            while True:
                batch = self._session.execute(
                    select(FilePage)
                    .where(FilePage.file_id == file_id)
                    .order_by(FilePage.page_number)
                    .offset(offset)
                    .limit(batch_size)
                ).scalars().all()
                if not batch:
                    break

                for file_page in batch:
                    self._render_and_store_page(document, pdf, file_page, image_format)
                    updated_pages.append(file_page)

                self._session.flush()
                offset += batch_size

        return updated_pages

    def _render_and_store_page(
        self,
        document: Document,
        pdf: fitz.Document,
        file_page: FilePage,
        image_format: str,
    ) -> None:
        file_page.status_preview = FilePageInitialStatus.PROCESSING.value
        self._session.flush()

        try:
            pdf_page = pdf.load_page(file_page.page_number - 1)
            pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image_bytes = pixmap.tobytes(image_format)
            object_key = (
                f"cases/{document.case_id}/documents/{document.id}/"
                f"previews/page-{file_page.page_number}.{image_format}"
            )
            self._storage.upload_document(
                file_stream=io.BytesIO(image_bytes),
                object_key=object_key,
                file_size=len(image_bytes),
                content_type=f"image/{image_format}",
                bucket=document.storage_bucket,
            )
            file_page.preview_storage_key = object_key
            file_page.status_preview = FilePageInitialStatus.COMPLETED.value
        except Exception:
            file_page.status_preview = FilePageInitialStatus.FAILED.value
            raise
