"""Model for technical limitations in a case."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class TechnicalLimitation(Base, UUIDPrimaryKey, TimestampMixin):
    """Limitação técnica — restrições técnicas identificadas durante a perícia."""

    __tablename__ = "technical_limitations"

    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    technical_impact: Mapped[str] = mapped_column(Text)
    criticality: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    diligence_id: Mapped[str | None] = mapped_column(
        ForeignKey("diligences.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quesito_id: Mapped[str | None] = mapped_column(
        ForeignKey("quesitos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    case: Mapped[Case] = relationship("Case", foreign_keys=[case_id])
    diligence: Mapped[Diligence | None] = relationship(
        "Diligence", foreign_keys=[diligence_id]
    )
    quesito: Mapped[Quesito | None] = relationship("Quesito", foreign_keys=[quesito_id])

    def __repr__(self) -> str:
        return f"<TechnicalLimitation(id={self.id}, case_id={self.case_id}, criticality={self.criticality})>"


from app.db.models.case import Case
from app.db.models.diligence import Diligence
from app.db.models.quesito import Quesito

__all__ = ["TechnicalLimitation"]
