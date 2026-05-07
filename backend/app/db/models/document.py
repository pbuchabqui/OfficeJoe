"""
Modelo de documento. O PDF original NUNCA é modificado.
O hash SHA-256 garante a integridade em todo o ciclo de vida.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"           # Recebido, aguardando processamento
    HASHING = "hashing"             # Calculando hash
    QUEUED_OCR = "queued_ocr"       # Na fila de OCR
    OCR_RUNNING = "ocr_running"     # OCR em andamento
    OCR_COMPLETED = "ocr_completed" # OCR concluído
    OCR_FAILED = "ocr_failed"       # Falha no OCR
    EXTRACTING = "extracting"       # Extração de dados em andamento
    INDEXED = "indexed"             # Embeddings gerados, pronto para busca
    ERROR = "error"
    ARCHIVED = "archived"


class DocumentCategory(str, Enum):
    AUTOS_PROCESSUAIS = "autos_processuais"
    HOLERITE = "holerite"
    CARTAO_PONTO = "cartao_ponto"
    FICHA_FINANCEIRA = "ficha_financeira"
    CONTRATO = "contrato"
    EXTRATO_BANCARIO = "extrato_bancario"
    LAUDO = "laudo"
    MANIFESTACAO = "manifestacao"
    DECISAO = "decisao"
    DOCUMENTO_CONTABIL = "documento_contabil"
    PLANILHA = "planilha"
    OUTRO = "outro"


class Document(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "documents"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Metadados do arquivo
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DocumentCategory.OUTRO.value
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Integridade – NUNCA alterar o arquivo original
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    total_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pdf_is_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_native_text: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Localização no storage (S3/MinIO)
    storage_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_version_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status do pipeline
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DocumentStatus.UPLOADED.value, index=True
    )
    ocr_engine_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ocr_avg_confidence: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Tarefas Celery
    ocr_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    embedding_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Controle
    is_original_preserved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uploaded_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relacionamentos
    case: Mapped["Case"] = relationship("Case", back_populates="documents")  # noqa: F821
    uploaded_by: Mapped[Optional["User"]] = relationship("User")  # noqa: F821
    pages: Mapped[List["Page"]] = relationship(  # noqa: F821
        "Page", back_populates="document", cascade="all, delete-orphan",
        order_by="Page.page_number",
    )
    extractions: Mapped[List["Extraction"]] = relationship(  # noqa: F821
        "Extraction", back_populates="document", cascade="all, delete-orphan"
    )
    ai_outputs: Mapped[List["AIOutput"]] = relationship(  # noqa: F821
        "AIOutput", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} file={self.original_filename} "
            f"status={self.status} sha256={self.sha256_hash[:12]}...>"
        )
