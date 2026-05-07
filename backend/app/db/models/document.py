"""
Modelo de arquivo recebido (File).

Representa o arquivo original recebido pelo sistema.
Princípio fundamental: o arquivo original é IMUTÁVEL após a ingestão.
O hash SHA-256 é calculado antes do armazenamento e verificável a qualquer momento.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.db.models.case import Case
    from app.db.models.user import User
    from app.db.models.custody_event import CustodyEvent


class IngestionStatus(str, Enum):
    """
    Estado do arquivo no pipeline de ingestão.
    Representa o status de processamento — não o estado do dado extraído.
    """
    RECEIVED = "received"           # Arquivo recebido, hash calculado
    QUEUED_OCR = "queued_ocr"       # Na fila para processamento OCR
    OCR_RUNNING = "ocr_running"     # OCR em andamento
    OCR_COMPLETED = "ocr_completed" # OCR concluído, texto bruto disponível
    OCR_FAILED = "ocr_failed"       # Falha no OCR
    CLASSIFIED = "classified"       # Tipo documental identificado
    INDEXED = "indexed"             # Embeddings gerados, busca semântica disponível
    ERROR = "error"                 # Erro irrecuperável no processamento
    ARCHIVED = "archived"           # Arquivado, não mais ativo


class File(Base, UUIDPrimaryKey, TimestampMixin):
    """
    Arquivo original recebido para um processo pericial.

    original_filename    – nome exato do arquivo conforme recebido; nunca alterado.
    display_name         – nome de exibição editável pelo usuário.
    sha256_hash          – hash SHA-256 do conteúdo binário do arquivo original.
                           Calculado por streaming antes do upload para o storage.
                           Verificável a qualquer momento via endpoint de integridade.
    file_size_bytes      – tamanho em bytes; registrado no momento da ingestão.
    mime_type            – tipo MIME do arquivo (esperado: application/pdf).
    storage_bucket       – nome do bucket no MinIO/S3.
    storage_key          – caminho único e imutável do objeto no storage.
                           Formato: cases/{case_id}/files/{file_id}/{filename}
    ingestion_status     – fase atual no pipeline de processamento.
    is_original_preserved – invariante de custódia; deve ser sempre TRUE.
                            Monitorado por verificações periódicas de integridade.
    total_pages          – número de páginas; preenchido após OCR.
    source_description   – descrição da origem do arquivo (ex: "Petição inicial").
                           Ajuda na classificação e no inventário dos autos.
    uploaded_by_id       – usuário que fez o upload; SET NULL se removido,
                           preservando o registro.
    """

    __tablename__ = "files"

    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Metadados do arquivo original — imutáveis após ingestão
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Integridade — invariante fundamental do sistema
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="application/pdf"
    )
    is_original_preserved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Localização no object storage
    storage_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Estado do pipeline
    ingestion_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=IngestionStatus.RECEIVED.value,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Contexto processual
    source_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rastreabilidade de quem enviou
    uploaded_by_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relacionamentos
    case: Mapped["Case"] = relationship("Case", back_populates="files")
    uploaded_by: Mapped[Optional["User"]] = relationship("User")
    custody_events: Mapped[List["CustodyEvent"]] = relationship(
        "CustodyEvent", back_populates="file", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<File id={self.id} name={self.original_filename} "
            f"sha256={self.sha256_hash[:12]}... status={self.ingestion_status}>"
        )
