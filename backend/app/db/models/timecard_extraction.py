"""Data models for structured timecard extraction.

This module only models storage for extracted timecard data. It does not
implement extraction algorithms, overtime calculations, exports, or UI flows.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class TimecardLayoutVariant(str, Enum):
    """Known broad layout families for timecard documents."""

    GENERICO = "generico"
    REP = "rep"
    ESPELHO_PONTO = "espelho_ponto"
    AFDT = "afdt"
    ACJEF = "acjef"
    OUTRO = "outro"


class TimecardExtractionStatus(str, Enum):
    PENDENTE = "pendente"
    EM_PROCESSAMENTO = "em_processamento"
    EXTRAIDO = "extraido"
    VALIDADO = "validado"
    REJEITADO = "rejeitado"
    ERRO = "erro"


class TimecardFieldValidationStatus(str, Enum):
    """Per-field validation state for each extracted daily mark."""

    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    CORRIGIDO = "corrigido"
    REJEITADO = "rejeitado"
    ILEGIVEL = "ilegivel"
    INCONSISTENTE = "inconsistente"


class TimecardDayValidationStatus(str, Enum):
    PENDENTE = "pendente"
    PARCIAL = "parcial"
    CONFIRMADO = "confirmado"
    CORRIGIDO = "corrigido"
    REJEITADO = "rejeitado"
    ILEGIVEL = "ilegivel"


class TimecardFieldType(str, Enum):
    """Fields that can be recorded for each timecard day.

    The model stores raw marks only. It intentionally avoids derived values
    such as overtime, night shift premiums, or balance calculations.
    """

    ENTRADA_1 = "entrada_1"
    SAIDA_1 = "saida_1"
    ENTRADA_2 = "entrada_2"
    SAIDA_2 = "saida_2"
    ENTRADA_3 = "entrada_3"
    SAIDA_3 = "saida_3"
    ENTRADA_4 = "entrada_4"
    SAIDA_4 = "saida_4"
    JUSTIFICATIVA = "justificativa"
    OCORRENCIA = "ocorrencia"
    OBSERVACAO = "observacao"
    OUTRO = "outro"


class TimecardExtraction(Base, UUIDPrimaryKey, TimestampMixin):
    """One timecard extraction found in a document."""

    __tablename__ = "timecard_extractions"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    evidence_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("evidence_items.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)

    competencia: Mapped[Optional[str]] = mapped_column(String(7), nullable=True, index=True)
    periodo_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    periodo_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    layout_variant: Mapped[str] = mapped_column(
        String(50), nullable=False, default=TimecardLayoutVariant.GENERICO.value,
    )
    layout_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    layout_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    extraction_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=TimecardExtractionStatus.PENDENTE.value, index=True,
    )

    unreadable_marks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unreadable_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="General notes about unreadable marks across the extracted timecard.",
    )

    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id])
    case: Mapped["Case"] = relationship("Case", foreign_keys=[case_id])
    evidence_item: Mapped[Optional["EvidenceItem"]] = relationship(
        "EvidenceItem", foreign_keys=[evidence_item_id],
    )
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])
    days: Mapped[list["TimecardDay"]] = relationship(
        "TimecardDay", back_populates="timecard",
        cascade="all, delete-orphan",
        order_by="TimecardDay.day_index",
    )

    def __repr__(self) -> str:
        return (
            f"<TimecardExtraction id={self.id} competencia={self.competencia} "
            f"status={self.extraction_status}>"
        )


class TimecardDay(Base, UUIDPrimaryKey, TimestampMixin):
    """One day row in a timecard extraction."""

    __tablename__ = "timecard_days"

    timecard_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("timecard_extractions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    file_page_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("file_pages.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    work_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    day_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weekday_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    raw_row: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    bbox_x0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=TimecardDayValidationStatus.PENDENTE.value, index=True,
    )
    unreadable_marks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unreadable_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Day-level notes for marks that are missing, blurred, cut off, or OCR-corrupted.",
    )
    corrected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    correction_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    validated_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    timecard: Mapped["TimecardExtraction"] = relationship(
        "TimecardExtraction", back_populates="days",
    )
    file_page: Mapped[Optional["FilePage"]] = relationship("FilePage", foreign_keys=[file_page_id])
    validated_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[validated_by_id])
    fields: Mapped[list["TimecardDayField"]] = relationship(
        "TimecardDayField", back_populates="day",
        cascade="all, delete-orphan",
        order_by="TimecardDayField.field_order",
    )

    __table_args__ = (
        UniqueConstraint("timecard_id", "day_index", name="uq_timecard_days_timecard_day_index"),
    )

    def __repr__(self) -> str:
        return (
            f"<TimecardDay timecard={self.timecard_id} idx={self.day_index} "
            f"date={self.work_date} status={self.validation_status}>"
        )


class TimecardDayField(Base, UUIDPrimaryKey, TimestampMixin):
    """Extracted field for one day, with validation status per field."""

    __tablename__ = "timecard_day_fields"

    day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("timecard_days.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    file_page_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("file_pages.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    field_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    field_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    raw_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Time marks should be normalized as HH:MM when legible.",
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    bbox_x0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_unreadable: Mapped[bool] = mapped_column(default=False, nullable=False)
    unreadable_note: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True,
        comment="Specific reason for unreadable mark, e.g. blur, overwritten text, or cut page.",
    )

    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=TimecardFieldValidationStatus.PENDENTE.value, index=True,
    )
    corrected_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    correction_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    validated_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    day: Mapped["TimecardDay"] = relationship("TimecardDay", back_populates="fields")
    file_page: Mapped[Optional["FilePage"]] = relationship("FilePage", foreign_keys=[file_page_id])
    validated_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[validated_by_id])

    __table_args__ = (
        UniqueConstraint("day_id", "field_type", "field_order", name="uq_timecard_day_fields_day_type_order"),
    )

    def __repr__(self) -> str:
        return (
            f"<TimecardDayField day={self.day_id} type={self.field_type} "
            f"value={self.normalized_value!r} status={self.validation_status}>"
        )


from app.db.models.case import Case                          # noqa: E402
from app.db.models.document import Document                  # noqa: E402
from app.db.models.evidence_item import EvidenceItem         # noqa: E402
from app.db.models.file_page import FilePage                 # noqa: E402
from app.db.models.user import User                          # noqa: E402

__all__ = [
    "TimecardExtraction",
    "TimecardDay",
    "TimecardDayField",
    "TimecardExtractionStatus",
    "TimecardFieldType",
    "TimecardFieldValidationStatus",
    "TimecardDayValidationStatus",
    "TimecardLayoutVariant",
]
