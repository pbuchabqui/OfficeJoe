"""
Registro de auditoria persistido no banco de dados.
Imutável por design – nunca deve ser atualizado, apenas inserido.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, String, Text, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKey
from sqlalchemy import DateTime
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base, UUIDPrimaryKey):
    __tablename__ = "audit_logs"

    # Imutável: sem TimestampMixin (updated_at não faz sentido)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    # Ação
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Ator
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Recurso afetado
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Processo relacionado (para rastreabilidade pericial)
    case_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Detalhes serializados
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relacionamentos (somente leitura)
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")  # noqa: F821
    case: Mapped[Optional["Case"]] = relationship("Case", back_populates="audit_logs")  # noqa: F821

    __table_args__ = (
        Index("ix_audit_logs_timestamp_action", "timestamp", "action"),
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_case_timestamp", "case_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action} "
            f"user={self.user_email} ts={self.timestamp}>"
        )
