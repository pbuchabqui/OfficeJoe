"""Model for evidence items extracted from documents."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import JSON, ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey
from app.core.evidence import EvidenceType, ReliabilityLevel


class EvidenceItem(Base, UUIDPrimaryKey, TimestampMixin):
    """Evidência extraída manualmente de um documento."""

    __tablename__ = "evidence_items"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int]
    text_excerpt: Mapped[str] = mapped_column(String(4000))
    coordinates: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    reliability_level: Mapped[int] = mapped_column(default=ReliabilityLevel.MEDIA)
    validated: Mapped[bool] = mapped_column(default=False)
    validation_status: Mapped[str] = mapped_column(String(50), default="pending")
    validated_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    case: Mapped[Case] = relationship("Case", foreign_keys=[case_id])
    document: Mapped[Document] = relationship("Document", foreign_keys=[document_id])
    validator: Mapped[User | None] = relationship("User", foreign_keys=[validated_by])

    def __repr__(self) -> str:
        return f"<EvidenceItem(id={self.id}, case_id={self.case_id}, type={self.evidence_type})>"


from app.db.models.case import Case
from app.db.models.document import Document
from app.db.models.user import User

__all__ = ["EvidenceItem"]
