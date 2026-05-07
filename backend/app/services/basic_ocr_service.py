"""
OCR básico por página lógica.
Usa texto nativo do PDF quando existir e Tesseract simples como fallback.
"""
from __future__ import annotations

import io
import uuid

import fitz
from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.document import Document
from app.db.models.file_page import FilePage, FilePageInitialStatus
from app.db.models.page_text_block import PageTextBlock
from app.services.storage_service import get_storage_service

settings = get_settings()


class BasicOCRService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._storage = get_storage_service()

    def process_file(self, file_id: str, batch_size: int = 10) -> list[FilePage]:
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

        processed: list[FilePage] = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
            offset = 0
            while True:
                pages = self._session.execute(
                    select(FilePage)
                    .where(FilePage.file_id == file_id)
                    .order_by(FilePage.page_number)
                    .offset(offset)
                    .limit(batch_size)
                ).scalars().all()
                if not pages:
                    break

                for file_page in pages:
                    self.process_page(pdf, file_page)
                    processed.append(file_page)
                self._session.flush()
                offset += batch_size

        return processed

    def process_page(self, pdf: fitz.Document, file_page: FilePage) -> list[PageTextBlock]:
        file_page.status_ocr = FilePageInitialStatus.PROCESSING.value
        self._session.flush()

        self._session.execute(
            delete(PageTextBlock).where(PageTextBlock.file_page_id == file_page.id)
        )
        page = pdf.load_page(file_page.page_number - 1)
        blocks = self._extract_native_blocks(page, file_page)

        if not blocks:
            blocks = self._extract_tesseract_blocks(page, file_page)

        for block in blocks:
            self._session.add(block)

        self._update_confidence_flags(file_page, blocks)
        file_page.status_ocr = FilePageInitialStatus.COMPLETED.value
        self._session.flush()
        return blocks

    def _update_confidence_flags(
        self,
        file_page: FilePage,
        blocks: list[PageTextBlock],
    ) -> None:
        confidences = [
            block.confidence
            for block in blocks
            if block.confidence is not None
        ]
        if not confidences:
            file_page.average_confidence = None
            file_page.low_confidence = True
            return

        average = sum(confidences) / len(confidences)
        file_page.average_confidence = average
        file_page.low_confidence = average < settings.OCR_LOW_CONFIDENCE_THRESHOLD

    def _extract_native_blocks(
        self,
        page: fitz.Page,
        file_page: FilePage,
    ) -> list[PageTextBlock]:
        words = page.get_text("words") or []
        blocks: list[PageTextBlock] = []
        for word in words:
            x0, y0, x1, y1, text = word[:5]
            text = str(text).strip()
            if not text:
                continue
            blocks.append(
                PageTextBlock(
                    id=str(uuid.uuid4()),
                    file_page_id=file_page.id,
                    file_id=file_page.file_id,
                    page_number=file_page.page_number,
                    text=text,
                    x0=float(x0),
                    y0=float(y0),
                    x1=float(x1),
                    y1=float(y1),
                    confidence=1.0,
                    source="native",
                )
            )
        return blocks

    def _extract_tesseract_blocks(
        self,
        page: fitz.Page,
        file_page: FilePage,
    ) -> list[PageTextBlock]:
        import pytesseract

        matrix = fitz.Matrix(2, 2)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        data = pytesseract.image_to_data(
            image,
            lang=settings.OCR_LANGUAGE,
            output_type=pytesseract.Output.DICT,
        )

        scale_x = file_page.width / image.width
        scale_y = file_page.height / image.height
        blocks: list[PageTextBlock] = []
        for i, raw_text in enumerate(data.get("text", [])):
            text = (raw_text or "").strip()
            if not text:
                continue
            try:
                confidence = float(data["conf"][i]) / 100
            except (ValueError, TypeError, KeyError):
                confidence = None
            if confidence is not None and confidence < 0:
                confidence = None

            x = float(data["left"][i]) * scale_x
            y = float(data["top"][i]) * scale_y
            width = float(data["width"][i]) * scale_x
            height = float(data["height"][i]) * scale_y
            blocks.append(
                PageTextBlock(
                    id=str(uuid.uuid4()),
                    file_page_id=file_page.id,
                    file_id=file_page.file_id,
                    page_number=file_page.page_number,
                    text=text,
                    x0=x,
                    y0=y,
                    x1=x + width,
                    y1=y + height,
                    confidence=confidence,
                    source="tesseract",
                )
            )
        return blocks
