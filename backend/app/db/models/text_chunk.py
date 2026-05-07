"""Chunks de texto com embeddings para busca semântica via pgvector."""
from __future__ import annotations

from sqlalchemy import String, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class TextChunk(Base, UUIDPrimaryKey, TimestampMixin):
    """Um segmento de texto extraído de um documento, com embedding para busca semântica."""

    __tablename__ = "text_chunks"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Vector pgvector: 384 dimensões (compatível com embeddings simples)
    embedding: Mapped[list[float]] = mapped_column(
        "embedding",
        nullable=False,
    )

    document: Mapped["Document"] = relationship("Document")  # noqa: F821

    def __repr__(self) -> str:
        return f"<TextChunk id={self.id} doc={self.document_id} page={self.page_number}>"
