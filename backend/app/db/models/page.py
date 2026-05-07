"""
Página extraída de um documento.
Mantém texto raw, status de OCR, confiança e coordenadas de bounding boxes.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class Page(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "pages"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Texto extraído via OCR/pdfplumber
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # OCR
    ocr_engine: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    has_text_layer: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )
    is_image_only: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )

    # Dimensões da página (pontos PDF)
    width_pt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_pt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Blocos de texto com coordenadas (lista de dicts: {text, x0, y0, x1, y1, confidence})
    text_blocks: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Tabelas detectadas na página (lista de dicts com estrutura da tabela)
    tables_detected: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Caminho para imagem da página renderizada (armazenada no MinIO)
    page_image_key: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relacionamento
    document: Mapped["Document"] = relationship("Document", back_populates="pages")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Page id={self.id} doc={self.document_id} "
            f"page={self.page_number} conf={self.ocr_confidence}>"
        )
