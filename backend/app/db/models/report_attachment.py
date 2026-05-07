"""Models for report annexes and appendices."""
from __future__ import annotations

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class ReportAttachmentType(str, Enum):
    ANEXO = "anexo"
    APENDICE = "apendice"


class ReportAttachment(Base, UUIDPrimaryKey, TimestampMixin):
    """Simple numbered annex or appendix linked to a report."""

    __tablename__ = "report_attachments"

    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    attachment_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    calculation_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("calculation_versions.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    report: Mapped["Report"] = relationship("Report", foreign_keys=[report_id])
    file: Mapped["Document | None"] = relationship("Document", foreign_keys=[file_id])
    calculation_version: Mapped["CalculationVersion | None"] = relationship(
        "CalculationVersion", foreign_keys=[calculation_version_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "attachment_type",
            "number",
            name="uq_report_attachments_report_type_number",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ReportAttachment report={self.report_id} "
            f"type={self.attachment_type} number={self.number}>"
        )


from app.db.models.calculation import CalculationVersion  # noqa: E402
from app.db.models.document import Document                # noqa: E402
from app.db.models.report import Report                    # noqa: E402

__all__ = ["ReportAttachment", "ReportAttachmentType"]
