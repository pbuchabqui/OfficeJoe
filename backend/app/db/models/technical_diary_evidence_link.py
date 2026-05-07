"""Model linking technical diary entries to evidence items."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class TechnicalDiaryEvidenceLink(Base, UUIDPrimaryKey, TimestampMixin):
    """Evidence supporting a technical diary entry."""

    __tablename__ = "technical_diary_evidence_links"

    technical_diary_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("technical_diary_entries.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    evidence_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    linked_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    technical_diary_entry: Mapped["TechnicalDiaryEntry"] = relationship(
        "TechnicalDiaryEntry", foreign_keys=[technical_diary_entry_id],
    )
    evidence_item: Mapped["EvidenceItem"] = relationship(
        "EvidenceItem", foreign_keys=[evidence_item_id],
    )
    linked_by: Mapped["User | None"] = relationship("User", foreign_keys=[linked_by_id])

    __table_args__ = (
        UniqueConstraint(
            "technical_diary_entry_id",
            "evidence_item_id",
            name="uq_technical_diary_evidence_links_entry_evidence",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TechnicalDiaryEvidenceLink entry={self.technical_diary_entry_id} "
            f"evidence={self.evidence_item_id}>"
        )


from app.db.models.evidence_item import EvidenceItem              # noqa: E402
from app.db.models.technical_diary_entry import TechnicalDiaryEntry  # noqa: E402
from app.db.models.user import User                               # noqa: E402

__all__ = ["TechnicalDiaryEvidenceLink"]
