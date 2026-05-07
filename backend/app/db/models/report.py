"""Models for initial report structure."""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class ReportStatus(str, Enum):
    RASCUNHO = "rascunho"
    EM_REVISAO = "em_revisao"
    FINAL = "final"
    ARQUIVADO = "arquivado"


class ReportSectionReviewStatus(str, Enum):
    PENDENTE = "pendente"
    EM_REVISAO = "em_revisao"
    APROVADA = "aprovada"


class Report(Base, UUIDPrimaryKey, TimestampMixin):
    """Initial report record for a case."""

    __tablename__ = "reports"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False,
        default=ReportStatus.RASCUNHO.value, index=True,
    )
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])
    sections: Mapped[list["ReportSection"]] = relationship(
        "ReportSection", back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportSection.section_order",
    )

    def __repr__(self) -> str:
        return (
            f"<Report id={self.id} case={self.case_id} "
            f"type={self.report_type!r} version={self.current_version}>"
        )


class ReportSection(Base, UUIDPrimaryKey, TimestampMixin):
    """Editable section inside a report."""

    __tablename__ = "report_sections"

    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    review_status: Mapped[str] = mapped_column(
        String(50), nullable=False,
        default=ReportSectionReviewStatus.PENDENTE.value, index=True,
    )
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    report: Mapped["Report"] = relationship("Report", back_populates="sections")

    __table_args__ = (
        UniqueConstraint("report_id", "section_order", name="uq_report_sections_report_order"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReportSection report={self.report_id} order={self.section_order} "
            f"title={self.title!r}>"
        )


from app.db.models.case import Case  # noqa: E402

__all__ = [
    "Report",
    "ReportSection",
    "ReportStatus",
    "ReportSectionReviewStatus",
]
