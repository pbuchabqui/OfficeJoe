"""Models for calculation control and immutable calculation file versions."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class CalculationStatus(str, Enum):
    RASCUNHO = "rascunho"
    EM_REVISAO = "em_revisao"
    APROVADO = "aprovado"
    ARQUIVADO = "arquivado"


class Calculation(Base, UUIDPrimaryKey, TimestampMixin):
    """Calculation control record for a case."""

    __tablename__ = "calculations"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    calculation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsible_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=CalculationStatus.RASCUNHO.value, index=True,
    )

    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])
    responsible_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[responsible_user_id],
    )
    versions: Mapped[list["CalculationVersion"]] = relationship(
        "CalculationVersion", back_populates="calculation",
        cascade="all, delete-orphan",
        order_by="CalculationVersion.version_number",
    )

    def __repr__(self) -> str:
        return (
            f"<Calculation id={self.id} case={self.case_id} "
            f"type={self.calculation_type!r} status={self.status}>"
        )


class CalculationVersion(Base, UUIDPrimaryKey, TimestampMixin):
    """Immutable uploaded file version for a calculation."""

    __tablename__ = "calculation_versions"

    calculation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("calculations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    premises: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    methodology: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    calculation: Mapped["Calculation"] = relationship(
        "Calculation", back_populates="versions",
    )
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        UniqueConstraint(
            "calculation_id",
            "version_number",
            name="uq_calculation_versions_calculation_version",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CalculationVersion calculation={self.calculation_id} "
            f"version={self.version_number} hash={self.sha256_hash[:12]}...>"
        )


from app.db.models.case import Case      # noqa: E402
from app.db.models.user import User      # noqa: E402

__all__ = [
    "Calculation",
    "CalculationVersion",
    "CalculationStatus",
]
