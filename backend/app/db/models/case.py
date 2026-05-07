"""
Modelo de processo pericial (Case).

Agrega todos os dados de um processo judicial ou extrajudicial.
É o contexto raiz de documentos, quesitos, laudos e auditoria.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.document import File
    from app.db.models.audit_log import AuditLog


class CaseStatus(str, Enum):
    """Fases do ciclo de vida pericial, na ordem cronológica esperada."""
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


class Case(Base, UUIDPrimaryKey, TimestampMixin):
    """
    Processo pericial.

    case_number      – número CNJ único do processo (formato NNNNNNN-DD.AAAA.J.TT.OOOO).
                       Chave de negócio imutável após criação.
    case_type        – natureza jurídica do processo.
    status           – fase atual conforme enum CaseStatus.
    title            – denominação resumida para listagens.
    description      – descrição livre para observações do perito.
    court            – vara ou tribunal onde tramita o processo.
    court_district   – comarca.
    judge_name       – juiz da causa (informativo).
    appointment_date – data da nomeação do perito pelo juízo.
    deadline_date    – prazo final para entrega do laudo; usado em alertas.
    filing_date      – data de protocolo do laudo finalizado.
    honorarium_*     – valores propostos e homologados em centavos (BIGINT).
    responsible_user – perito responsável; SET NULL se o usuário for excluído,
                       preservando o registro do processo.
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
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Informações do juízo
    court: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    court_district: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    judge_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Datas processuais
    appointment_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    deadline_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    filing_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Honorários em centavos — evita imprecisão de ponto flutuante
    honorarium_proposed_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    honorarium_approved_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Perito responsável
    responsible_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relacionamentos
    responsible_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="cases"
    )
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="case", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="case", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} number={self.case_number} status={self.status}>"
