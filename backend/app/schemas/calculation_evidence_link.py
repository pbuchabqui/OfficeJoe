"""Schemas for linking calculation versions to evidence."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CalculationEvidenceLinkRequest(BaseModel):
    evidence_item_id: str = Field(..., description="ID da evidência a vincular")


class CalculationEvidenceAlert(BaseModel):
    level: str
    message: str
    evidence_item_id: str


class CalculationEvidenceLinkResponse(BaseModel):
    id: str
    calculation_version_id: str
    evidence_item_id: str
    linked_by_id: str | None
    created_at: datetime
    alert: CalculationEvidenceAlert | None = None


class CalculationEvidenceUnlinkResponse(BaseModel):
    calculation_version_id: str
    evidence_item_id: str
    removed: bool
