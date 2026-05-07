from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.db.models.case import CaseStatus, CaseType, ProcessualPhase

# Regex CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO
_CNJ_PATTERN = re.compile(r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")

_VALID_STATUSES = {e.value for e in CaseStatus}
_VALID_TYPES = {e.value for e in CaseType}
_VALID_PHASES = {e.value for e in ProcessualPhase}


# ── Partes processuais ────────────────────────────────────────────────────────

class CasePartyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=500)
    role: str = Field(..., min_length=2, max_length=50)
    cpf_cnpj: Optional[str] = None
    lawyer_name: Optional[str] = None
    lawyer_oab: Optional[str] = None


class CasePartyResponse(BaseModel):
    id: str
    case_id: str
    name: str
    role: str
    cpf_cnpj: Optional[str]
    lawyer_name: Optional[str]
    lawyer_oab: Optional[str]
    model_config = {"from_attributes": True}


# ── Processo ──────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    case_number: str = Field(..., description="Número CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO")
    case_type: str
    title: str = Field(..., min_length=3, max_length=500)

    # Dados do juízo
    tribunal: Optional[str] = Field(None, max_length=255)
    vara: Optional[str] = Field(None, max_length=255)
    court_district: Optional[str] = Field(None, max_length=255)

    # Fase e objeto
    fase_processual: Optional[str] = None
    objeto_pericia: Optional[str] = None

    # Datas (ISO YYYY-MM-DD)
    appointment_date: Optional[str] = None
    data_ciencia: Optional[str] = None
    deadline_date: Optional[str] = None

    # Observações
    notes: Optional[str] = None

    # Honorários em centavos
    honorarium_proposed_cents: Optional[int] = Field(None, ge=0)

    # Partes
    parties: List[CasePartyCreate] = []

    @field_validator("case_number")
    @classmethod
    def validate_cnj(cls, v: str) -> str:
        v = v.strip()
        if not _CNJ_PATTERN.match(v):
            raise ValueError(
                "Número CNJ inválido. Formato esperado: NNNNNNN-DD.AAAA.J.TT.OOOO"
            )
        return v

    @field_validator("case_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in _VALID_TYPES:
            raise ValueError(
                f"Tipo inválido. Opções: {', '.join(sorted(_VALID_TYPES))}"
            )
        return v

    @field_validator("fase_processual")
    @classmethod
    def validate_phase(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_PHASES:
            raise ValueError(
                f"Fase inválida. Opções: {', '.join(sorted(_VALID_PHASES))}"
            )
        return v

    @field_validator("appointment_date", "data_ciencia", "deadline_date", mode="before")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            from datetime import date
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Data inválida. Use o formato YYYY-MM-DD.")
        return v


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    status: Optional[str] = None
    tribunal: Optional[str] = Field(None, max_length=255)
    vara: Optional[str] = Field(None, max_length=255)
    court_district: Optional[str] = Field(None, max_length=255)
    fase_processual: Optional[str] = None
    objeto_pericia: Optional[str] = None
    appointment_date: Optional[str] = None
    data_ciencia: Optional[str] = None
    deadline_date: Optional[str] = None
    notes: Optional[str] = None
    honorarium_proposed_cents: Optional[int] = Field(None, ge=0)
    honorarium_approved_cents: Optional[int] = Field(None, ge=0)
    responsible_user_id: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_STATUSES:
            raise ValueError(
                f"Status inválido. Opções: {', '.join(sorted(_VALID_STATUSES))}"
            )
        return v

    @field_validator("fase_processual")
    @classmethod
    def validate_phase(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_PHASES:
            raise ValueError(
                f"Fase inválida. Opções: {', '.join(sorted(_VALID_PHASES))}"
            )
        return v

    @field_validator("appointment_date", "data_ciencia", "deadline_date", mode="before")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            from datetime import date
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Data inválida. Use o formato YYYY-MM-DD.")
        return v


# ── Respostas ─────────────────────────────────────────────────────────────────

class CaseSummary(BaseModel):
    id: str
    case_number: str
    case_type: str
    status: str
    title: str
    tribunal: Optional[str]
    vara: Optional[str]
    court_district: Optional[str]
    fase_processual: Optional[str]
    deadline_date: Optional[str]
    responsible_user_id: Optional[str]
    model_config = {"from_attributes": True}


class CaseDetail(CaseSummary):
    objeto_pericia: Optional[str]
    appointment_date: Optional[str]
    data_ciencia: Optional[str]
    filing_date: Optional[str]
    notes: Optional[str]
    honorarium_proposed_cents: Optional[int]
    honorarium_approved_cents: Optional[int]
    parties: List[CasePartyResponse] = []
    deleted_at: Optional[str]
    model_config = {"from_attributes": True}


class PaginatedCases(BaseModel):
    items: List[CaseSummary]
    total: int
    page: int
    size: int
    pages: int
