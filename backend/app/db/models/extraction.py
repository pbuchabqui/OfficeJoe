"""
Extração estruturada de dados de páginas.
Toda extração mantém vínculo com arquivo, página e coordenadas.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class ExtractionType(str, Enum):
    TEXT_BLOCK = "text_block"
    TABLE = "table"
    ENTITY_CPF = "entity_cpf"
    ENTITY_CNPJ = "entity_cnpj"
    ENTITY_DATE = "entity_date"
    ENTITY_CURRENCY = "entity_currency"
    ENTITY_PERSON = "entity_person"
    ENTITY_COMPANY = "entity_company"
    PAYSLIP_FIELD = "payslip_field"         # Campo de holerite
    TIMECARD_ENTRY = "timecard_entry"       # Entrada de cartão ponto
    FINANCIAL_ENTRY = "financial_entry"     # Lançamento financeiro
    CONTRACT_CLAUSE = "contract_clause"     # Cláusula contratual
    BANK_STATEMENT_ROW = "bank_statement_row"
    CALCULATION_VALUE = "calculation_value"


class Extraction(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "extractions"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("pages.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Rastreabilidade obrigatória
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Coordenadas na página (em pontos PDF)
    bbox_x0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Conteúdo extraído
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Confiança e revisão
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extrator usado
    extractor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extractor_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relacionamentos
    document: Mapped["Document"] = relationship("Document", back_populates="extractions")  # noqa: F821
    page: Mapped[Optional["Page"]] = relationship("Page")  # noqa: F821
    reviewed_by: Mapped[Optional["User"]] = relationship("User")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Extraction id={self.id} type={self.extraction_type} "
            f"page={self.page_number} conf={self.confidence}>"
        )
