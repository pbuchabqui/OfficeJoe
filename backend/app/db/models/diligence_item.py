"""Model for diligence items (individual requests within a diligence)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class DiligenceItem(Base, UUIDPrimaryKey, TimestampMixin):
    """Item de diligência - uma solicitação específica dentro de uma diligência."""

    __tablename__ = "diligence_items"

    diligence_id: Mapped[str] = mapped_column(
        ForeignKey("diligences.id", ondelete="CASCADE"), index=True
    )
    requested_document: Mapped[str] = mapped_column(String(500))
    period: Mapped[str] = mapped_column(String(200))
    technical_justification: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    diligence: Mapped[Diligence] = relationship(
        "Diligence", foreign_keys=[diligence_id], back_populates="items"
    )

    def __repr__(self) -> str:
        return f"<DiligenceItem(id={self.id}, diligence_id={self.diligence_id}, status={self.status})>"


from app.db.models.diligence import Diligence

__all__ = ["DiligenceItem"]
