"""Data models for structured financial statement extraction.

This module only models storage for extracted ficha financeira data. It does
not implement extraction algorithms, calculations, exports, or comparisons
with other document types.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class FinancialStatementLayoutVariant(str, Enum):
    """Known broad layout families for ficha financeira documents."""

    GENERICO = "generico"
    FOLHA_ANALITICA = "folha_analitica"
    FICHA_FINANCEIRA = "ficha_financeira"
    RELATORIO_RH = "relatorio_rh"
    OUTRO = "outro"


class FinancialStatementExtractionStatus(str, Enum):
    PENDENTE = "pendente"
    EM_PROCESSAMENTO = "em_processamento"
    EXTRAIDO = "extraido"
    VALIDADO = "validado"
    REJEITADO = "rejeitado"
    ERRO = "erro"


class FinancialStatementValidationStatus(str, Enum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    CORRIGIDO = "corrigido"
    REJEITADO = "rejeitado"
    ILEGIVEL = "ilegivel"
    INCONSISTENTE = "inconsistente"


class FinancialRubricType(str, Enum):
    PROVENTO = "provento"
    DESCONTO = "desconto"
    INFORMATIVO = "informativo"
    BASE = "base"
    OUTRO = "outro"


class FinancialStatementExtraction(Base, UUIDPrimaryKey, TimestampMixin):
    """One ficha financeira extraction identified in a document."""

    __tablename__ = "financial_statement_extractions"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    evidence_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("evidence_items.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)

    periodo_inicio: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True,
        comment="Initial competency in MM/YYYY format when identifiable.",
    )
    periodo_fim: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True,
        comment="Final competency in MM/YYYY format when identifiable.",
    )

    layout_variant: Mapped[str] = mapped_column(
        String(50), nullable=False, default=FinancialStatementLayoutVariant.GENERICO.value,
    )
    layout_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    layout_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    extraction_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=FinancialStatementExtractionStatus.PENDENTE.value, index=True,
    )

    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id])
    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])
    evidence_item: Mapped[Optional["EvidenceItem"]] = relationship(
        "EvidenceItem", foreign_keys=[evidence_item_id],
    )
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])
    competencies: Mapped[list["FinancialStatementCompetency"]] = relationship(
        "FinancialStatementCompetency", back_populates="financial_statement",
        cascade="all, delete-orphan",
        order_by="FinancialStatementCompetency.competencia",
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialStatementExtraction id={self.id} "
            f"period={self.periodo_inicio}-{self.periodo_fim} status={self.extraction_status}>"
        )


class FinancialStatementCompetency(Base, UUIDPrimaryKey, TimestampMixin):
    """Competency/month block extracted from a ficha financeira."""

    __tablename__ = "financial_statement_competencies"

    financial_statement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("financial_statement_extractions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    file_page_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("file_pages.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    competencia: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True,
        comment="Competency in MM/YYYY format.",
    )
    competencia_raw: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    section_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_section: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    bbox_x0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=FinancialStatementValidationStatus.PENDENTE.value, index=True,
    )
    corrected_competencia: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    correction_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    validated_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    financial_statement: Mapped["FinancialStatementExtraction"] = relationship(
        "FinancialStatementExtraction", back_populates="competencies",
    )
    file_page: Mapped[Optional["FilePage"]] = relationship("FilePage", foreign_keys=[file_page_id])
    validated_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[validated_by_id])
    rubrics: Mapped[list["FinancialStatementRubric"]] = relationship(
        "FinancialStatementRubric", back_populates="competency",
        cascade="all, delete-orphan",
        order_by="FinancialStatementRubric.line_index",
    )

    __table_args__ = (
        UniqueConstraint(
            "financial_statement_id",
            "competencia",
            "section_index",
            name="uq_financial_statement_competencies_statement_competencia_section",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialStatementCompetency statement={self.financial_statement_id} "
            f"competencia={self.competencia} status={self.validation_status}>"
        )


class FinancialStatementRubric(Base, UUIDPrimaryKey, TimestampMixin):
    """Rubric/value extracted for a specific competency."""

    __tablename__ = "financial_statement_rubrics"

    competency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("financial_statement_competencies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    file_page_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("file_pages.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    line_index: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    descricao: Mapped[str] = mapped_column(String(250), nullable=False)
    rubric_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=FinancialRubricType.OUTRO.value, index=True,
    )

    referencia_raw: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    referencia_normalized: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    valor_raw: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    valor_decimal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_row: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    bbox_x0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=FinancialStatementValidationStatus.PENDENTE.value, index=True,
    )
    corrected_referencia: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    corrected_valor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    corrected_rubric_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    correction_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    validated_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    competency: Mapped["FinancialStatementCompetency"] = relationship(
        "FinancialStatementCompetency", back_populates="rubrics",
    )
    file_page: Mapped[Optional["FilePage"]] = relationship("FilePage", foreign_keys=[file_page_id])
    validated_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[validated_by_id])

    __table_args__ = (
        UniqueConstraint(
            "competency_id",
            "line_index",
            name="uq_financial_statement_rubrics_competency_line",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FinancialStatementRubric competency={self.competency_id} "
            f"codigo={self.codigo!r} value={self.valor_decimal} status={self.validation_status}>"
        )


from app.db.models.case import Case                          # noqa: E402
from app.db.models.document import Document                  # noqa: E402
from app.db.models.evidence_item import EvidenceItem         # noqa: E402
from app.db.models.file_page import FilePage                 # noqa: E402
from app.db.models.user import User                          # noqa: E402

__all__ = [
    "FinancialStatementExtraction",
    "FinancialStatementCompetency",
    "FinancialStatementRubric",
    "FinancialStatementExtractionStatus",
    "FinancialStatementLayoutVariant",
    "FinancialStatementValidationStatus",
    "FinancialRubricType",
]
