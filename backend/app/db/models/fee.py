"""Models for initial expert fee control."""
from __future__ import annotations

from enum import Enum
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class FeeStatus(str, Enum):
    PROPOSTO = "proposto"
    ARBITRADO = "arbitrado"
    DEPOSITADO = "depositado"
    LEVANTADO = "levantado"
    CANCELADO = "cancelado"


class Fee(Base, UUIDPrimaryKey, TimestampMixin):
    """Initial fee record linked to a case."""

    __tablename__ = "fees"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    proposed_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    arbitrated_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    deposited_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    withdrawn_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=FeeStatus.PROPOSTO.value,
        index=True,
    )
    proposed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    arbitrated_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    deposited_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    withdrawn_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])

    def __repr__(self) -> str:
        return f"<Fee case={self.case_id} status={self.status} proposed={self.proposed_amount}>"


from app.db.models.case import Case  # noqa: E402

__all__ = ["Fee", "FeeStatus"]
