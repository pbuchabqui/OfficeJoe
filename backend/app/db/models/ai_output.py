"""
Saídas de IA com rastreabilidade completa.
Todo output indica fontes, páginas, grau de confiança e status de revisão humana.
Nenhuma conclusão técnica sem lastro documental.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import Float, ForeignKey, String, Text, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class AIOutputType(str, Enum):
    SUMMARY = "summary"                     # Resumo de documento/processo
    QUESITO_DRAFT = "quesito_draft"         # Rascunho de resposta a quesito
    ENTITY_EXTRACTION = "entity_extraction" # Extração de entidades
    TABLE_ANALYSIS = "table_analysis"       # Análise de tabela
    CALCULATION_REVIEW = "calculation_review"
    DOCUMENT_CLASSIFICATION = "document_classification"
    SEMANTIC_SEARCH = "semantic_search"
    ANOMALY_DETECTION = "anomaly_detection"
    TIMELINE_EXTRACTION = "timeline_extraction"
    CHAT = "chat"


class AIReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIALLY_APPROVED = "partially_approved"


class AIOutput(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "ai_outputs"

    # Contexto
    case_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quesito_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("quesitos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Tipo e identificação
    output_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Modelo
    ai_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Resposta
    output_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # RASTREABILIDADE OBRIGATÓRIA
    # Lista de fontes: [{document_id, document_name, page_number, extraction_id, excerpt, confidence}]
    sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Confiança agregada (0.0 a 1.0)
    overall_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Revisão humana
    review_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=AIReviewStatus.PENDING_REVIEW.value, index=True
    )
    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_documental_basis: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Quem solicitou
    requested_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relacionamentos
    document: Mapped[Optional["Document"]] = relationship(  # noqa: F821
        "Document", back_populates="ai_outputs"
    )
    reviewed_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", foreign_keys=[reviewed_by_id]
    )
    requested_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", foreign_keys=[requested_by_id]
    )

    def __repr__(self) -> str:
        return (
            f"<AIOutput id={self.id} type={self.output_type} "
            f"model={self.ai_model} review={self.review_status}>"
        )
