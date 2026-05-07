"""Model for document contradiction findings.

Contradictions record compared extracted values. They are technical flags for
review, not merit conclusions.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class DocumentContradictionStatus(str, Enum):
    PENDENTE = "pendente"
    CONFIRMADA = "confirmada"
    DESCARTADA = "descartada"


class DocumentContradiction(Base, UUIDPrimaryKey, TimestampMixin):
    """A single contradiction found between extracted document values."""

    __tablename__ = "document_contradictions"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    competencia: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    holerite_extraction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("holerite_extractions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    holerite_verba_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("holerite_verbas.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    financial_statement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("financial_statement_extractions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    financial_statement_rubric_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("financial_statement_rubrics.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    rubric_key: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    rubric_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    rubric_description: Mapped[str] = mapped_column(String(300), nullable=False)

    holerite_value_raw: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    holerite_value_decimal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    financial_value_raw: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    financial_value_decimal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    delta_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    compared_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=DocumentContradictionStatus.PENDENTE.value, index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])
    holerite_extraction: Mapped["HoleriteExtraction"] = relationship(
        "HoleriteExtraction", foreign_keys=[holerite_extraction_id],
    )
    holerite_verba: Mapped["HoleriteVerba"] = relationship(
        "HoleriteVerba", foreign_keys=[holerite_verba_id],
    )
    financial_statement: Mapped["FinancialStatementExtraction"] = relationship(
        "FinancialStatementExtraction", foreign_keys=[financial_statement_id],
    )
    financial_statement_rubric: Mapped["FinancialStatementRubric"] = relationship(
        "FinancialStatementRubric", foreign_keys=[financial_statement_rubric_id],
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentContradiction case={self.case_id} competencia={self.competencia} "
            f"rubric={self.rubric_key!r} status={self.status}>"
        )


from app.db.models.case import Case                                      # noqa: E402
from app.db.models.financial_statement_extraction import (               # noqa: E402
    FinancialStatementExtraction,
    FinancialStatementRubric,
)
from app.db.models.holerite_extraction import HoleriteExtraction, HoleriteVerba  # noqa: E402

__all__ = [
    "DocumentContradiction",
    "DocumentContradictionStatus",
]
