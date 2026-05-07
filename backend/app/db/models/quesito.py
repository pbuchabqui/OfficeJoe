"""
Quesitos periciais e suas respostas fundamentadas.
Nenhuma resposta técnica sem lastro documental.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class QuesitoStatus(str, Enum):
    PENDENTE = "pendente"
    EM_ANALISE = "em_analise"
    RESPONDIDO = "respondido"
    REVISADO = "revisado"
    APROVADO = "aprovado"


class QuesitoOrigin(str, Enum):
    JUIZO = "juizo"
    PARTE_AUTORA = "parte_autora"
    PARTE_RE = "parte_re"
    ASSISTENTE_TECNICO = "assistente_tecnico"
    PROPRIO = "proprio"  # Elaborado pelo perito


class Quesito(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "quesitos"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Identificação
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[str] = mapped_column(
        String(50), nullable=False, default=QuesitoOrigin.JUIZO.value
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=QuesitoStatus.PENDENTE.value, index=True
    )

    # Texto do quesito
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relacionamentos
    case: Mapped["Case"] = relationship("Case", back_populates="quesitos")  # noqa: F821
    answers: Mapped[List["QuesitoAnswer"]] = relationship(
        "QuesitoAnswer", back_populates="quesito", cascade="all, delete-orphan",
        order_by="QuesitoAnswer.version",
    )

    def __repr__(self) -> str:
        return f"<Quesito id={self.id} seq={self.sequence_number} status={self.status}>"


class QuesitoAnswer(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "quesito_answers"

    quesito_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("quesitos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Resposta
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Lastro documental OBRIGATÓRIO – lista de refs {document_id, page_number, extraction_id, excerpt}
    document_references: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # IA
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Revisão humana obrigatória para conclusões técnicas
    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Elaborado por
    authored_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relacionamentos
    quesito: Mapped["Quesito"] = relationship("Quesito", back_populates="answers")
    reviewed_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", foreign_keys=[reviewed_by_id]
    )
    authored_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", foreign_keys=[authored_by_id]
    )

    def __repr__(self) -> str:
        return (
            f"<QuesitoAnswer id={self.id} quesito={self.quesito_id} "
            f"v={self.version} reviewed={self.is_human_reviewed}>"
        )
