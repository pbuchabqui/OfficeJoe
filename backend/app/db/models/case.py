"""
Modelo de processo pericial (Case).
Representa um processo judicial ou extrajudicial com toda a sua estrutura.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Text, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class CaseStatus(str, Enum):
    PLANEJAMENTO = "planejamento"       # Fase inicial, análise dos autos
    DILIGENCIAS = "diligencias"          # Coleta de documentos/informações
    ANALISE = "analise"                  # Análise dos documentos
    CALCULOS = "calculos"                # Realização de cálculos periciais
    LAUDO_RASCUNHO = "laudo_rascunho"   # Elaboração do laudo
    LAUDO_REVISAO = "laudo_revisao"     # Revisão final
    LAUDO_PROTOCOLADO = "laudo_protocolado"  # Laudo entregue ao juízo
    ESCLARECIMENTOS = "esclarecimentos" # Fase de esclarecimentos
    ENCERRADO = "encerrado"
    SUSPENSO = "suspenso"


class CaseType(str, Enum):
    TRABALHISTA = "trabalhista"
    CIVEL = "civel"
    FISCAL = "fiscal"
    EXTRAJUDICIAL = "extrajudicial"
    ARBITRAGEM = "arbitragem"


class Case(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "cases"

    # Identificação processual
    case_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    case_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=CaseStatus.PLANEJAMENTO.value, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Informações do juízo
    court: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    court_district: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    judge_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Datas
    appointment_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    deadline_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    filing_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Honorários
    honorarium_proposed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    honorarium_approved: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Responsável
    responsible_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relacionamentos
    responsible_user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", back_populates="cases"
    )
    parties: Mapped[List["CaseParty"]] = relationship(
        "CaseParty", back_populates="case", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(  # noqa: F821
        "Document", back_populates="case", cascade="all, delete-orphan"
    )
    quesitos: Mapped[List["Quesito"]] = relationship(  # noqa: F821
        "Quesito", back_populates="case", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(  # noqa: F821
        "AuditLog", back_populates="case", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} number={self.case_number} status={self.status}>"


class PartyRole(str, Enum):
    RECLAMANTE = "reclamante"
    RECLAMADO = "reclamado"
    AUTOR = "autor"
    REU = "reu"
    ASSISTENTE_TECNICO_AUTOR = "assistente_tecnico_autor"
    ASSISTENTE_TECNICO_REU = "assistente_tecnico_reu"
    JUIZ = "juiz"
    PROMOTOR = "promotor"
    OUTRO = "outro"


class CaseParty(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "case_parties"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    cpf_cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    lawyer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lawyer_oab: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="parties")

    def __repr__(self) -> str:
        return f"<CaseParty id={self.id} name={self.name} role={self.role}>"
