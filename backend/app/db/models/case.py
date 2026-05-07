"""
Modelo de processo pericial (Case) e partes processuais (CaseParty).

Case é o contexto-raiz de todos os documentos, quesitos, laudos e auditoria.
CaseParty representa reclamante, reclamado, advogados e demais envolvidos.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.document import File
    from app.db.models.audit_log import AuditLog


class CaseStatus(str, Enum):
    """Status interno do ciclo de vida pericial (workflow do escritório)."""
    PLANEJAMENTO = "planejamento"
    DILIGENCIAS = "diligencias"
    ANALISE = "analise"
    CALCULOS = "calculos"
    LAUDO_RASCUNHO = "laudo_rascunho"
    LAUDO_REVISAO = "laudo_revisao"
    LAUDO_PROTOCOLADO = "laudo_protocolado"
    ESCLARECIMENTOS = "esclarecimentos"
    ENCERRADO = "encerrado"
    SUSPENSO = "suspenso"


class CaseType(str, Enum):
    TRABALHISTA = "trabalhista"
    CIVEL = "civel"
    FISCAL = "fiscal"
    EXTRAJUDICIAL = "extrajudicial"
    ARBITRAGEM = "arbitragem"


class ProcessualPhase(str, Enum):
    """Fase processual vigente no juízo (independente do status interno)."""
    CITACAO = "citacao"
    INSTRUCAO = "instrucao"
    PERICIA = "pericia"
    SENTENCA = "sentenca"
    RECURSO = "recurso"
    EXECUCAO = "execucao"
    LIQUIDACAO = "liquidacao"
    ARQUIVADO = "arquivado"


class Case(Base, UUIDPrimaryKey, TimestampMixin):
    """
    Processo pericial.

    case_number      – número CNJ único (NNNNNNN-DD.AAAA.J.TT.OOOO). Imutável.
    case_type        – natureza jurídica (CaseType).
    status           – fase interna do workflow do escritório (CaseStatus).
    tribunal         – nome do tribunal (ex: TRT-2, TJSP, STJ).
    vara             – vara ou câmara onde o processo tramita.
    court_district   – comarca.
    fase_processual  – fase processual formal no juízo (ProcessualPhase).
    objeto_pericia   – descrição do objeto e escopo da perícia.
    appointment_date – data da nomeação pelo juízo (ISO YYYY-MM-DD).
    data_ciencia     – data em que o perito tomou ciência da nomeação.
    deadline_date    – prazo final para entrega do laudo.
    deleted_at       – soft delete; NULL = ativo.
    honorarium_*     – valores em centavos (BIGINT) para evitar float.
    responsible_user – perito responsável; SET NULL na exclusão do usuário.
    """

    __tablename__ = "cases"

    case_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    case_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=CaseStatus.PLANEJAMENTO.value,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # Dados do juízo
    tribunal: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vara: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    court_district: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Fase e objeto
    fase_processual: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    objeto_pericia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Datas processuais (ISO 8601 como string para evitar dependência de tz)
    appointment_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    data_ciencia: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    deadline_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    filing_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Observações internas
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Honorários em centavos
    honorarium_proposed_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    honorarium_approved_cents: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Perito responsável
    responsible_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Soft delete — NULL = ativo; preenchido = excluído logicamente
    deleted_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relacionamentos
    responsible_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="cases"
    )
    parties: Mapped[List["CaseParty"]] = relationship(
        "CaseParty",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="case", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="case", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} number={self.case_number} status={self.status}>"


class CaseParty(Base, UUIDPrimaryKey):
    """Parte processual vinculada a um processo."""

    __tablename__ = "case_parties"

    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    cpf_cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    lawyer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lawyer_oab: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="parties")

    def __repr__(self) -> str:
        return f"<CaseParty case={self.case_id} role={self.role} name={self.name}>"
