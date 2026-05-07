"""Schemas for document contradiction comparison."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentContradictionCompareRequest(BaseModel):
    case_id: str = Field(..., description="ID do processo")
    competencia: str = Field(..., pattern=r"^\d{2}/\d{4}$", description="Competência MM/AAAA")


class ComparedDocumentValue(BaseModel):
    extraction_id: str
    item_id: str
    value_raw: str | None
    value_decimal: float | None


class DocumentContradictionResponse(BaseModel):
    id: str
    case_id: str
    competencia: str
    rule_key: str
    rubric_key: str
    rubric_code: str | None
    rubric_description: str
    holerite: ComparedDocumentValue
    financial_statement: ComparedDocumentValue
    delta_value: float | None
    status: str
    created_at: datetime


class DocumentContradictionComparisonResult(BaseModel):
    case_id: str
    competencia: str
    rule_key: str
    compared_count: int
    contradiction_count: int
    contradictions: list[DocumentContradictionResponse] = Field(default_factory=list)
