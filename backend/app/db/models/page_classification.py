"""Classificação documental por página."""
from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class DocumentClass(str, Enum):
    HOLERITE = "holerite"
    FICHA_FINANCEIRA = "ficha financeira"
    CARTAO_PONTO = "cartão ponto"
    SENTENCA = "sentença"
    ACORDAO = "acórdão"
    DECISAO = "decisão"
    PETICAO_INICIAL = "petição inicial"
    CONTESTACAO = "contestação"
    LAUDO = "laudo"
    PARECER = "parecer"
    CONTRATO = "contrato"
    EXTRATO = "extrato"
    NOTA_FISCAL = "nota fiscal"
    CCT = "CCT"
    ACT = "ACT"
    TRCT = "TRCT"
    EMAIL = "e-mail"
    PLANILHA = "planilha"
    DOCUMENTO_ILEGIVEL = "documento ilegível"
    OUTRO = "outro"


class PageClassification(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "page_classifications"

    file_page_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("file_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(nullable=False, index=True)
    document_class: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    human_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validated_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    file_page: Mapped["FilePage"] = relationship("FilePage")  # noqa: F821
    file: Mapped["Document"] = relationship("Document")  # noqa: F821
    validator: Mapped[Optional["User"]] = relationship("User")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("file_page_id", name="uq_page_classifications_file_page_id"),
    )
