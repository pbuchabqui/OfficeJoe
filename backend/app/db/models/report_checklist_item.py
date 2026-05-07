"""Model for initial normative report checklist items."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class ReportChecklistItem(Base, UUIDPrimaryKey, TimestampMixin):
    """Checklist item for a report."""

    __tablename__ = "report_checklist_items"

    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    item_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="incompleto", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    report: Mapped["Report"] = relationship("Report", foreign_keys=[report_id])
    updated_by: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_id])

    __table_args__ = (
        UniqueConstraint("report_id", "item_key", name="uq_report_checklist_items_report_key"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReportChecklistItem report={self.report_id} key={self.item_key!r} "
            f"status={self.status}>"
        )


from app.db.models.report import Report  # noqa: E402
from app.db.models.user import User      # noqa: E402

__all__ = ["ReportChecklistItem"]
