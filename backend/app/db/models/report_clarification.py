"""Models for report clarification requests."""
from __future__ import annotations

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class ReportClarificationStatus(str, Enum):
    RECEBIDO = "recebido"
    EM_ANALISE = "em_analise"
    RESPONDIDO = "respondido"
    ARQUIVADO = "arquivado"


class ReportClarification(Base, UUIDPrimaryKey, TimestampMixin):
    """Initial clarification request linked to a report."""

    __tablename__ = "report_clarifications"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    report_version: Mapped[int] = mapped_column(Integer, nullable=False)
    request_text: Mapped[str] = mapped_column(Text, nullable=False)
    theme: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReportClarificationStatus.RECEBIDO.value,
        index=True,
    )
    preliminary_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])
    report: Mapped["Report"] = relationship("Report", foreign_keys=[report_id])

    def __repr__(self) -> str:
        return (
            f"<ReportClarification report={self.report_id} "
            f"version={self.report_version} theme={self.theme!r}>"
        )


from app.db.models.case import Case      # noqa: E402
from app.db.models.report import Report  # noqa: E402

__all__ = ["ReportClarification", "ReportClarificationStatus"]
