"""Schemas for report clarifications."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReportClarificationCreateRequest(BaseModel):
    report_id: str
    request_text: str = Field(..., min_length=1)
    theme: str = Field(..., min_length=1, max_length=200)
    status: str = "recebido"
    preliminary_response: str | None = None
    final_response: str | None = None


class ReportClarificationUpdateRequest(BaseModel):
    request_text: str | None = Field(None, min_length=1)
    theme: str | None = Field(None, min_length=1, max_length=200)
    status: str | None = None
    preliminary_response: str | None = None
    final_response: str | None = None


class ReportClarificationResponse(BaseModel):
    id: str
    case_id: str
    report_id: str
    report_version: int
    request_text: str
    theme: str
    status: str
    preliminary_response: str | None
    final_response: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportClarificationPaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ReportClarificationResponse]
