"""
Modelo de evento de cadeia de custódia (CustodyEvent).

Registro imutável de toda operação realizada sobre um arquivo.
Sem updated_at — eventos de custódia nunca são editados.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.db.models.document import File
    from app.db.models.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CustodyEventType(str, Enum):
    """
    Tipos de evento possíveis na cadeia de custódia.
    Cada tipo representa uma ação auditável sobre o arquivo original.
    """
    # Ciclo de vida fundamental (obrigatórios pelo prompt 9)
    UPLOADED = "uploaded"                       # Arquivo recebido e armazenado
    HASH_CALCULATED = "hash_calculated"         # SHA-256 calculado e registrado
    VIEWED = "viewed"                           # Arquivo visualizado por usuário
    DOWNLOADED = "downloaded"                   # Arquivo baixado por usuário
    DERIVED_CREATED = "derived_created"         # Arquivo derivado criado (ex: página extraída)
    REPROCESSED = "reprocessed"                 # Arquivo reprocessado (novo OCR, etc.)
    INTEGRITY_CHECKED = "integrity_checked"     # Verificação de integridade bem-sucedida
    INTEGRITY_FAIL = "integrity_fail"           # Hash não confere — alerta crítico

    # Eventos adicionais do pipeline
    EXPORT_GENERATED = "export_generated"       # Exportação/cópia gerada
    OCR_STARTED = "ocr_started"                 # Pipeline OCR iniciado
    OCR_COMPLETED = "ocr_completed"             # Pipeline OCR concluído
    OCR_FAILED = "ocr_failed"                   # Pipeline OCR falhou
    DELETION_REQUESTED = "deletion_requested"   # Solicitação de remoção registrada


class CustodyEvent(Base, UUIDPrimaryKey):
    """
    Evento imutável na cadeia de custódia de um arquivo.

    file_id                  – arquivo ao qual o evento se refere.
    event_type               – tipo da operação realizada.
    event_at                 – timestamp UTC exato do evento; gerado no servidor.
    actor_user_id            – usuário que disparou o evento (NULL para ações automáticas).
    actor_ip                 – endereço IP do ator humano, quando aplicável.
    integrity_hash_verified  – hash SHA-256 lido do storage no momento da verificação.
                               Comparado com files.sha256_hash para confirmar integridade.
    integrity_ok             – resultado da comparação (NULL quando não aplicável).
    notes                    – observações livres sobre o evento.

    Nota: sem updated_at — este registro nunca deve ser modificado após a inserção.
    """

    __tablename__ = "custody_events"

    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    # Ator humano — pode ser NULL para ações automáticas do sistema
    actor_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Campos específicos de verificação de integridade
    integrity_hash_verified: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    integrity_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relacionamentos (somente leitura)
    file: Mapped["File"] = relationship("File", back_populates="custody_events")
    actor_user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CustodyEvent id={self.id} type={self.event_type} "
            f"file={self.file_id} at={self.event_at}>"
        )
