"""Schemas for expert fee control."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class FeeCreateRequest(BaseModel):
    proposed_amount: float | None = Field(None, ge=0)
    arbitrated_amount: float | None = Field(None, ge=0)
    deposited_amount: float | None = Field(None, ge=0)
    withdrawn_amount: float | None = Field(None, ge=0)
    status: str = "proposto"
    proposed_at: date | None = None
    arbitrated_at: date | None = None
    deposited_at: date | None = None
    withdrawn_at: date | None = None
    notes: str | None = None


class FeeUpdateRequest(BaseModel):
    proposed_amount: float | None = Field(None, ge=0)
    arbitrated_amount: float | None = Field(None, ge=0)
    deposited_amount: float | None = Field(None, ge=0)
    withdrawn_amount: float | None = Field(None, ge=0)
    status: str | None = None
    proposed_at: date | None = None
    arbitrated_at: date | None = None
    deposited_at: date | None = None
    withdrawn_at: date | None = None
    notes: str | None = None


class FeeResponse(BaseModel):
    id: str
    case_id: str
    proposed_amount: float | None
    arbitrated_amount: float | None
    deposited_amount: float | None
    withdrawn_amount: float | None
    status: str
    proposed_at: date | None
    arbitrated_at: date | None
    deposited_at: date | None
    withdrawn_at: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeePaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[FeeResponse]
