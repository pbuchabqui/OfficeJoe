"""Model linking calculation versions to evidence items."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class CalculationEvidenceLink(Base, UUIDPrimaryKey, TimestampMixin):
    """Evidence used by a specific immutable calculation version."""

    __tablename__ = "calculation_evidence_links"

    calculation_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("calculation_versions.id", ondelete="CASCADE"),
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

    calculation_version: Mapped["CalculationVersion"] = relationship(
        "CalculationVersion", foreign_keys=[calculation_version_id],
    )
    evidence_item: Mapped["EvidenceItem"] = relationship(
        "EvidenceItem", foreign_keys=[evidence_item_id],
    )
    linked_by: Mapped["User | None"] = relationship("User", foreign_keys=[linked_by_id])

    __table_args__ = (
        UniqueConstraint(
            "calculation_version_id",
            "evidence_item_id",
            name="uq_calculation_evidence_links_version_evidence",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CalculationEvidenceLink version={self.calculation_version_id} "
            f"evidence={self.evidence_item_id}>"
        )


from app.db.models.calculation import CalculationVersion  # noqa: E402
from app.db.models.evidence_item import EvidenceItem      # noqa: E402
from app.db.models.user import User                       # noqa: E402

__all__ = ["CalculationEvidenceLink"]
