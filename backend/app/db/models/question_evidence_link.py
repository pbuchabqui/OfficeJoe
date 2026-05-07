"""Link between quesitos and evidence items."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class QuestionEvidenceLink(Base, UUIDPrimaryKey, TimestampMixin):
    """Link between a Quesito and an EvidenceItem."""

    __tablename__ = "question_evidence_links"

    quesito_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("quesitos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationship to quesito
    quesito: Mapped["Quesito"] = relationship("Quesito", back_populates="evidence_links")  # noqa: F821
    evidence_item: Mapped["EvidenceItem"] = relationship("EvidenceItem")  # noqa: F821

    def __repr__(self) -> str:
        return f"<QuestionEvidenceLink quesito={self.quesito_id} evidence={self.evidence_item_id}>"


from app.db.models.quesito import Quesito
from app.db.models.evidence_item import EvidenceItem

__all__ = ["QuestionEvidenceLink"]
