"""Model for diligences (requests for additional information/documents)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class Diligence(Base, UUIDPrimaryKey, TimestampMixin):
    """Diligência - solicitação de documentos ou informações adicionais em processo."""

    __tablename__ = "diligences"

    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[str] = mapped_column(String(100), unique=True)
    recipient: Mapped[str] = mapped_column(String(500))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="draft")
    observations: Mapped[str] = mapped_column(Text, default="")

    case: Mapped[Case] = relationship("Case", foreign_keys=[case_id])
    items: Mapped[list[DiligenceItem]] = relationship(
        "DiligenceItem", back_populates="diligence", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Diligence(id={self.id}, number={self.number}, case_id={self.case_id})>"


from app.db.models.case import Case
from app.db.models.diligence_item import DiligenceItem

__all__ = ["Diligence"]
