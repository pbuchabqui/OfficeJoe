"""
Modelos para extração estruturada de holerites.

Três tabelas:
  holerite_extractions  — um registro por holerite identificado no documento
  holerite_fields       — campos de cabeçalho/totais com status de validação por campo
  holerite_verbas       — linhas de proventos e descontos com status por linha
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HoleriteLayoutVariant(str, Enum):
    """Layouts mais comuns de holerite no mercado brasileiro.

    Não existe formato legal obrigatório; cada sistema de RH tem template
    próprio. O variant é detectado automaticamente (campo layout_confidence)
    e pode ser corrigido manualmente via layout_metadata.
    """
    GENERICO = "generico"           # Formato desconhecido / artesanal
    ESOCIAL = "esocial"             # PDF gerado a partir de XML eSocial (S-1200)
    TOTVS_PROTHEUS = "totvs_protheus"
    SAP_HR = "sap_hr"               # SAP HCM / SuccessFactors
    SENIOR = "senior"               # Senior Sistemas (RH Senior)
    DOMINIO = "dominio"             # Domínio Sistemas (Thomson Reuters)
    FOLHA_CERTA = "folha_certa"
    OUTRO = "outro"


class HoleriteExtractionStatus(str, Enum):
    PENDENTE = "pendente"
    EM_PROCESSAMENTO = "em_processamento"
    EXTRAIDO = "extraido"           # Extração concluída, aguarda revisão
    VALIDADO = "validado"           # Todos os campos revisados e aprovados
    REJEITADO = "rejeitado"         # Documento ilegível ou não é holerite
    ERRO = "erro"


class HoleriteFieldType(str, Enum):
    """Campos de cabeçalho, identificação e totais de um holerite.

    Não cobre as linhas de verbas individuais, que ficam em HoleriteVerba.
    Campos com múltiplos layouts têm normalized_value padronizado
    (e.g. CPF sempre "NNN.NNN.NNN-NN"; competência sempre "MM/AAAA").
    """
    # Dados do empregado
    NOME_EMPREGADO = "nome_empregado"
    CPF_EMPREGADO = "cpf_empregado"
    PIS_PASEP = "pis_pasep"
    MATRICULA = "matricula"
    DATA_ADMISSAO = "data_admissao"
    CARGO = "cargo"
    CBO = "cbo"
    DEPARTAMENTO = "departamento"
    CTPS_NUMERO = "ctps_numero"
    CTPS_SERIE = "ctps_serie"

    # Dados do empregador
    NOME_EMPRESA = "nome_empresa"
    CNPJ_EMPRESA = "cnpj_empresa"
    CNAE_EMPRESA = "cnae_empresa"
    ENDERECO_EMPRESA = "endereco_empresa"

    # Período de referência
    COMPETENCIA = "competencia"          # "MM/AAAA"
    DIAS_TRABALHADOS = "dias_trabalhados"
    HORAS_TRABALHADAS = "horas_trabalhadas"

    # Totais financeiros (sempre presentes em holerite válido)
    SALARIO_BASE = "salario_base"
    TOTAL_PROVENTOS = "total_proventos"
    TOTAL_DESCONTOS = "total_descontos"
    SALARIO_LIQUIDO = "salario_liquido"

    # FGTS
    BASE_FGTS = "base_fgts"
    VALOR_FGTS = "valor_fgts"
    SALDO_FGTS = "saldo_fgts"           # Saldo acumulado (nem sempre presente)

    # INSS
    BASE_INSS = "base_inss"
    VALOR_INSS = "valor_inss"
    ALIQUOTA_INSS = "aliquota_inss"     # Percentual aplicado

    # IRRF
    BASE_IRRF = "base_irrf"
    VALOR_IRRF = "valor_irrf"
    DEDUCOES_IRRF = "deducoes_irrf"
    DEPENDENTES_IRRF = "dependentes_irrf"

    # Banco de horas
    BANCO_HORAS_SALDO = "banco_horas_saldo"

    OUTRO = "outro"


class HoleriteFieldValidationStatus(str, Enum):
    """Status de validação aplicado campo a campo e verba a verba."""
    PENDENTE = "pendente"               # Ainda não revisado
    CONFIRMADO = "confirmado"           # Valor conferido e correto
    CORRIGIDO = "corrigido"             # Valor estava errado; corrected_value preenchido
    REJEITADO = "rejeitado"             # Campo não extraível ou ilegível
    INCONSISTENTE = "inconsistente"     # Inconsistência detectada (e.g. soma não fecha)


class VerbaTipo(str, Enum):
    PROVENTO = "provento"               # Crédito ao empregado
    DESCONTO = "desconto"               # Débito do empregado
    INFORMATIVO = "informativo"         # Linha sem impacto no líquido (e.g. base FGTS)


# ---------------------------------------------------------------------------
# Tabela 1: holerite_extractions
# ---------------------------------------------------------------------------

class HoleriteExtraction(Base, UUIDPrimaryKey, TimestampMixin):
    """Um holerite identificado dentro de um documento.

    Um documento pode conter vários holerites (e.g. PDF com 12 meses);
    cada um gera uma linha nesta tabela. page_start/page_end delimitam
    as páginas do documento que correspondem a este holerite.
    """
    __tablename__ = "holerite_extractions"

    # --- Vínculos obrigatórios ---
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Vínculo opcional com EvidenceItem: preenchido quando o holerite é
    # promovido a evidência formal no processo
    evidence_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("evidence_items.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # --- Localização no documento ---
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Identificação do período ---
    # Normalizado como "MM/AAAA"; nullable até a extração confirmar
    competencia: Mapped[Optional[str]] = mapped_column(String(7), nullable=True, index=True)

    # --- Layout detectado ---
    layout_variant: Mapped[str] = mapped_column(
        String(50), nullable=False, default=HoleriteLayoutVariant.GENERICO.value,
    )
    # Confiança na detecção do layout (0.0–1.0)
    layout_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Metadados adicionais dependentes do layout (template_id, versão, etc.)
    layout_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # --- Status geral da extração ---
    extraction_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=HoleriteExtractionStatus.PENDENTE.value, index=True,
    )

    # --- Verificação matemática: proventos − descontos = líquido ---
    math_check_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    # Diferença encontrada em string para preservar precisão decimal
    math_check_delta: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    math_check_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Revisão humana ---
    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Relacionamentos ---
    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id])
    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])
    evidence_item: Mapped[Optional["EvidenceItem"]] = relationship(
        "EvidenceItem", foreign_keys=[evidence_item_id],
    )
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])
    fields: Mapped[list["HoleriteField"]] = relationship(
        "HoleriteField", back_populates="holerite",
        cascade="all, delete-orphan",
        order_by="HoleriteField.field_type",
    )
    verbas: Mapped[list["HoleriteVerba"]] = relationship(
        "HoleriteVerba", back_populates="holerite",
        cascade="all, delete-orphan",
        order_by="HoleriteVerba.line_index",
    )

    def __repr__(self) -> str:
        return (
            f"<HoleriteExtraction id={self.id} competencia={self.competencia} "
            f"status={self.extraction_status}>"
        )


# ---------------------------------------------------------------------------
# Tabela 2: holerite_fields
# ---------------------------------------------------------------------------

class HoleriteField(Base, UUIDPrimaryKey, TimestampMixin):
    """Campo individual de cabeçalho ou total de um holerite.

    Cada campo tem raw_value (como extraído) e normalized_value (limpo e
    padronizado). O status de validação é individual por campo para permitir
    revisão incremental: um perito pode confirmar o CPF antes de revisar
    o salário líquido.

    Campos ausentes no documento original não geram linha; a ausência de
    uma linha para um field_type esperado é, em si, informação (evidência
    de layout incompleto ou documento parcial).
    """
    __tablename__ = "holerite_fields"

    # --- Vínculo ---
    holerite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("holerite_extractions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # Página específica onde o campo foi localizado (nullable para campos
    # que aparecem em layouts sem coordenadas precisas)
    file_page_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("file_pages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Tipo do campo ---
    field_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # --- Valor extraído ---
    raw_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Normalizado: datas → ISO 8601; valores monetários → "NNNN.NN"; CPF → "NNN.NNN.NNN-NN"
    normalized_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Coordenadas na página (em pontos PDF, origem canto superior esquerdo) ---
    bbox_x0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Validação ---
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=HoleriteFieldValidationStatus.PENDENTE.value, index=True,
    )
    corrected_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    correction_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    validated_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Relacionamentos ---
    holerite: Mapped["HoleriteExtraction"] = relationship(
        "HoleriteExtraction", back_populates="fields",
    )
    file_page: Mapped[Optional["FilePage"]] = relationship("FilePage", foreign_keys=[file_page_id])
    validated_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[validated_by_id])

    __table_args__ = (
        # Um campo de cada tipo por holerite (evita duplicatas na extração)
        UniqueConstraint("holerite_id", "field_type", name="uq_holerite_fields_holerite_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<HoleriteField holerite={self.holerite_id} type={self.field_type} "
            f"val={self.normalized_value!r} status={self.validation_status}>"
        )


# ---------------------------------------------------------------------------
# Tabela 3: holerite_verbas
# ---------------------------------------------------------------------------

class HoleriteVerba(Base, UUIDPrimaryKey, TimestampMixin):
    """Linha individual de provento, desconto ou informativo de um holerite.

    Cada verba (rubrica) aparece como uma linha separada. line_index preserva
    a ordem original do documento para reconciliação com o papel.

    valor_decimal é null quando a linha não pôde ser parseada para número
    (e.g. referência sem valor monetário, linha de título de seção).
    Nesses casos raw_row contém o texto completo para auditoria.
    """
    __tablename__ = "holerite_verbas"

    # --- Vínculo ---
    holerite_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("holerite_extractions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    file_page_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("file_pages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Ordem no documento ---
    line_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Dados da verba ---
    # codigo: código interno do sistema de RH (e.g. "001", "HEXT50", "0101")
    # Pode ser nulo em layouts que omitem código
    codigo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    # referencia: horas, dias, percentual — exatamente como aparece no documento
    referencia: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # valor como string preservando formatação original (e.g. "1.234,56")
    valor_raw: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # valor parseado para float; null se não parseável
    valor_decimal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tipo: Mapped[str] = mapped_column(
        String(15), nullable=False, default=VerbaTipo.INFORMATIVO.value,
    )

    # --- Linha bruta completa (para auditoria e re-extração) ---
    raw_row: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Coordenadas da linha na página ---
    bbox_x0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Confiança da extração ---
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Validação ---
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=HoleriteFieldValidationStatus.PENDENTE.value, index=True,
    )
    corrected_valor: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    corrected_tipo: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    correction_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    validated_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Relacionamentos ---
    holerite: Mapped["HoleriteExtraction"] = relationship(
        "HoleriteExtraction", back_populates="verbas",
    )
    file_page: Mapped[Optional["FilePage"]] = relationship("FilePage", foreign_keys=[file_page_id])
    validated_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[validated_by_id])

    def __repr__(self) -> str:
        return (
            f"<HoleriteVerba holerite={self.holerite_id} idx={self.line_index} "
            f"desc={self.descricao!r} tipo={self.tipo} val={self.valor_decimal}>"
        )


# Imports resolvidos após definição das classes para evitar referências circulares
from app.db.models.case import Case                          # noqa: E402
from app.db.models.document import Document                  # noqa: E402
from app.db.models.evidence_item import EvidenceItem         # noqa: E402
from app.db.models.file_page import FilePage                 # noqa: E402
from app.db.models.user import User                          # noqa: E402

__all__ = [
    "HoleriteExtraction",
    "HoleriteField",
    "HoleriteVerba",
    "HoleriteExtractionStatus",
    "HoleriteFieldType",
    "HoleriteFieldValidationStatus",
    "HoleriteLayoutVariant",
    "VerbaTipo",
]
