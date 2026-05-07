"""Model for evidence matrix items (proof matrix)."""
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class EvidenceMatrixItem(Base, UUIDPrimaryKey, TimestampMixin):
    """Item da matriz de prova vinculando fatos controversos a evidências."""

    __tablename__ = "evidence_matrix_items"

    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    disputed_fact: Mapped[str] = mapped_column(String(1000))
    theme: Mapped[str] = mapped_column(String(500))
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    expert_procedure: Mapped[str] = mapped_column(String(500), default="")
    methodology_or_criteria: Mapped[str] = mapped_column(Text, default="")
    result_found: Mapped[str] = mapped_column(Text, default="")
    technical_impact: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="draft")

    case: Mapped[Case] = relationship("Case", foreign_keys=[case_id])

    def __repr__(self) -> str:
        return f"<EvidenceMatrixItem(id={self.id}, case_id={self.case_id}, fact={self.disputed_fact})>"


from app.db.models.case import Case

__all__ = ["EvidenceMatrixItem"]
