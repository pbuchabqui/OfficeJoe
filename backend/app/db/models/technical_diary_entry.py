"""Model for technical diary entries."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class TechnicalDiaryEntry(Base, UUIDPrimaryKey, TimestampMixin):
    """Technical decision diary entry for a case."""

    __tablename__ = "technical_diary_entries"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    responsible_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    technical_justification: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])
    responsible_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[responsible_user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<TechnicalDiaryEntry id={self.id} case={self.case_id} "
            f"date={self.entry_date} type={self.decision_type!r}>"
        )


from app.db.models.case import Case  # noqa: E402
from app.db.models.user import User  # noqa: E402

__all__ = ["TechnicalDiaryEntry"]
