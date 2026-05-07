"""Schemas Pydantic para extração de holerites."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models.holerite_extraction import (
    HoleriteExtractionStatus,
    HoleriteFieldType,
    HoleriteFieldValidationStatus,
    HoleriteLayoutVariant,
    VerbaTipo,
)


# ---------------------------------------------------------------------------
# HoleriteField schemas
# ---------------------------------------------------------------------------

class HoleriteFieldResponse(BaseModel):
    id: str
    holerite_id: str
    file_page_id: Optional[str]
    field_type: str
    raw_value: Optional[str]
    normalized_value: Optional[str]
    confidence: Optional[float]
    bbox_x0: Optional[float]
    bbox_y0: Optional[float]
    bbox_x1: Optional[float]
    bbox_y1: Optional[float]
    validation_status: str
    corrected_value: Optional[str]
    correction_note: Optional[str]
    validated_by_id: Optional[str]
    validated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HoleriteFieldValidateRequest(BaseModel):
    """Atualiza o status de validação de um campo individual."""
    validation_status: HoleriteFieldValidationStatus
    corrected_value: Optional[str] = Field(
        None,
        description="Obrigatório quando validation_status = CORRIGIDO",
    )
    correction_note: Optional[str] = None


# ---------------------------------------------------------------------------
# HoleriteVerba schemas
# ---------------------------------------------------------------------------

class HoleriteVerbaResponse(BaseModel):
    id: str
    holerite_id: str
    file_page_id: Optional[str]
    line_index: int
    codigo: Optional[str]
    descricao: str
    referencia: Optional[str]
    valor_raw: Optional[str]
    valor_decimal: Optional[float]
    tipo: str
    raw_row: Optional[str]
    bbox_x0: Optional[float]
    bbox_y0: Optional[float]
    bbox_x1: Optional[float]
    bbox_y1: Optional[float]
    confidence: Optional[float]
    validation_status: str
    corrected_valor: Optional[str]
    corrected_tipo: Optional[str]
    correction_note: Optional[str]
    validated_by_id: Optional[str]
    validated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HoleriteVerbaValidateRequest(BaseModel):
    """Atualiza o status de validação de uma verba individual."""
    validation_status: HoleriteFieldValidationStatus
    corrected_valor: Optional[str] = Field(
        None,
        description="Valor corrigido (string); obrigatório quando status = CORRIGIDO",
    )
    corrected_tipo: Optional[VerbaTipo] = Field(
        None,
        description="Tipo corrigido quando o tipo foi mal classificado",
    )
    correction_note: Optional[str] = None


# ---------------------------------------------------------------------------
# HoleriteExtraction schemas
# ---------------------------------------------------------------------------

class HoleriteExtractionResponse(BaseModel):
    """Resposta completa com campos e verbas."""
    id: str
    document_id: str
    case_id: str
    evidence_item_id: Optional[str]
    page_start: int
    page_end: int
    competencia: Optional[str]
    layout_variant: str
    layout_confidence: Optional[float]
    layout_metadata: Optional[dict]
    extraction_status: str
    math_check_passed: Optional[bool]
    math_check_delta: Optional[str]
    math_check_notes: Optional[str]
    reviewed_by_id: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    fields: list[HoleriteFieldResponse] = []
    verbas: list[HoleriteVerbaResponse] = []

    model_config = {"from_attributes": True}


class HoleriteExtractionSummary(BaseModel):
    """Resposta resumida para listagem — sem campos e verbas."""
    id: str
    document_id: str
    case_id: str
    evidence_item_id: Optional[str]
    page_start: int
    page_end: int
    competencia: Optional[str]
    layout_variant: str
    layout_confidence: Optional[float]
    extraction_status: str
    math_check_passed: Optional[bool]
    reviewed_by_id: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HoleriteExtractionUpdateRequest(BaseModel):
    """Atualizações manuais permitidas sobre uma extração."""
    competencia: Optional[str] = Field(None, pattern=r"^\d{2}/\d{4}$")
    layout_variant: Optional[HoleriteLayoutVariant] = None
    extraction_status: Optional[HoleriteExtractionStatus] = None
    evidence_item_id: Optional[str] = None


class HoleriteExtractionPaginatedResponse(BaseModel):
    items: list[HoleriteExtractionSummary]
    total: int
    limit: int
    offset: int
