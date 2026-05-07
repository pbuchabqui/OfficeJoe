"""
Modelo de log de auditoria (AuditLog).

Registro imutável de toda ação relevante do sistema.
Sem updated_at — logs de auditoria nunca são editados.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, Index
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.case import Case


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base, UUIDPrimaryKey):
    """
    Entrada imutável do log de auditoria.

    timestamp      – momento exato da ação no servidor (UTC).
    action         – identificador da ação no formato dominio.operacao
                     (ex: auth.login_success, document.upload, evidence.validated).
    success        – resultado da ação; FALSE indica tentativa falha ou erro.
    user_id        – usuário que executou a ação (FK com SET NULL para preservar
                     o log mesmo após remoção do usuário).
    user_email     – email desnormalizado; mantém legibilidade histórica mesmo
                     após exclusão do usuário.
    ip_address     – endereço IP do cliente; IPv4 ou IPv6 (max 45 chars para IPv6).
    user_agent     – cabeçalho User-Agent; auxilia em investigações de segurança.
    case_id        – processo relacionado à ação, quando aplicável.
    resource_type  – tipo do recurso afetado (ex: "file", "case", "user").
    resource_id    – UUID do recurso afetado.
    details        – payload JSONB com contexto adicional da ação
                     (ex: nome do arquivo, hash, motivo de falha).

    Nota: sem updated_at — este registro nunca deve ser modificado após inserção.
    """

    __tablename__ = "audit_logs"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Ator
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Contexto do processo
    case_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Recurso afetado
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Payload contextual
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relacionamentos somente leitura
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    case: Mapped[Optional["Case"]] = relationship("Case", back_populates="audit_logs")

    __table_args__ = (
        # Consultas frequentes: auditoria por período + tipo de ação
        Index("ix_audit_logs_timestamp_action", "timestamp", "action"),
        # Rastreamento de todas as ações de um usuário
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        # Histórico completo de um processo
        Index("ix_audit_logs_case_timestamp", "case_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action} "
            f"user={self.user_email} ok={self.success}>"
        )
