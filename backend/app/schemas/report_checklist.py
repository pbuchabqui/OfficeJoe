"""Schemas for report checklist items."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReportChecklistItemUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(completo|incompleto|nao_aplicavel)$")
    notes: str | None = None


class ReportChecklistItemResponse(BaseModel):
    id: str
    report_id: str
    item_key: str
    title: str
    item_order: int
    status: str
    notes: str | None
    updated_by_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportChecklistResponse(BaseModel):
    report_id: str
    total: int
    items: list[ReportChecklistItemResponse]


class ReportChecklistExportValidationItem(BaseModel):
    item_id: str
    item_key: str
    title: str
    status: str
    blocking: bool


class ReportChecklistExportValidationResponse(BaseModel):
    report_id: str
    can_export: bool
    blocking_count: int
    blocking_items: list[ReportChecklistExportValidationItem]
    message: str
