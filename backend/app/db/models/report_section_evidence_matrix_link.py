"""Model linking report sections to evidence matrix items."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class ReportSectionEvidenceMatrixLink(Base, UUIDPrimaryKey, TimestampMixin):
    """Evidence matrix item referenced by a report section."""

    __tablename__ = "report_section_evidence_matrix_links"

    report_section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("report_sections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    evidence_matrix_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_matrix_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    linked_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    report_section: Mapped["ReportSection"] = relationship(
        "ReportSection", foreign_keys=[report_section_id],
    )
    evidence_matrix_item: Mapped["EvidenceMatrixItem"] = relationship(
        "EvidenceMatrixItem", foreign_keys=[evidence_matrix_item_id],
    )
    linked_by: Mapped["User | None"] = relationship("User", foreign_keys=[linked_by_id])

    __table_args__ = (
        UniqueConstraint(
            "report_section_id",
            "evidence_matrix_item_id",
            name="uq_report_section_matrix_links_section_matrix",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ReportSectionEvidenceMatrixLink section={self.report_section_id} "
            f"matrix={self.evidence_matrix_item_id}>"
        )


from app.db.models.evidence_matrix_item import EvidenceMatrixItem  # noqa: E402
from app.db.models.report import ReportSection                     # noqa: E402
from app.db.models.user import User                                # noqa: E402

__all__ = ["ReportSectionEvidenceMatrixLink"]
