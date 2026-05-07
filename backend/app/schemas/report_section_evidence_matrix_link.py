"""Schemas for report section to evidence matrix links."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReportSectionEvidenceMatrixLinkRequest(BaseModel):
    evidence_matrix_item_id: str = Field(..., description="ID do item da matriz de prova")


class ReportSectionEvidenceMatrixAlert(BaseModel):
    level: str
    message: str
    evidence_matrix_item_id: str


class ReportSectionEvidenceMatrixLinkResponse(BaseModel):
    id: str
    report_section_id: str
    evidence_matrix_item_id: str
    linked_by_id: str | None
    created_at: datetime
    alert: ReportSectionEvidenceMatrixAlert | None = None


class ReportSectionEvidenceMatrixUnlinkResponse(BaseModel):
    report_section_id: str
    evidence_matrix_item_id: str
    removed: bool
