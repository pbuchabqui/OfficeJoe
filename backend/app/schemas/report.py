"""Schemas for reports and report sections."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    report_type: str = Field(..., min_length=1, max_length=100)
    status: str = "rascunho"


class ReportUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    report_type: str | None = Field(None, min_length=1, max_length=100)
    status: str | None = None


class ReportSectionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    section_order: int = Field(..., ge=1)
    content: str = ""
    review_status: str = "pendente"


class ReportSectionUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    section_order: int | None = Field(None, ge=1)
    content: str | None = None
    review_status: str | None = None


class ReportSectionResponse(BaseModel):
    id: str
    report_id: str
    title: str
    section_order: int
    content: str
    review_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: str
    case_id: str
    title: str
    report_type: str
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportWithSectionsResponse(ReportResponse):
    sections: list[ReportSectionResponse] = []


class ReportPaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ReportResponse]
