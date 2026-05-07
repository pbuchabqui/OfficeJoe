"""Schemas for technical diary entries."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TechnicalDiaryEntryCreateRequest(BaseModel):
    entry_date: date
    responsible_user_id: str | None = None
    decision_type: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    technical_justification: str = Field(..., min_length=1)
    status: str = "draft"


class TechnicalDiaryEntryUpdateRequest(BaseModel):
    entry_date: date | None = None
    responsible_user_id: str | None = None
    decision_type: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1)
    technical_justification: str | None = Field(None, min_length=1)
    status: str | None = None


class TechnicalDiaryEntryResponse(BaseModel):
    id: str
    case_id: str
    entry_date: date
    responsible_user_id: str | None
    decision_type: str
    description: str
    technical_justification: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TechnicalDiaryEntryPaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TechnicalDiaryEntryResponse]
