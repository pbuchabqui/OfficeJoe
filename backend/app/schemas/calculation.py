"""Schemas for calculation control."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CalculationCreateRequest(BaseModel):
    calculation_type: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    responsible_user_id: str | None = None
    status: str = "rascunho"


class CalculationResponse(BaseModel):
    id: str
    case_id: str
    calculation_type: str
    description: str | None
    responsible_user_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CalculationVersionResponse(BaseModel):
    id: str
    calculation_id: str
    version_number: int
    original_filename: str
    storage_bucket: str
    storage_key: str
    sha256_hash: str
    file_size_bytes: int
    mime_type: str
    premises: str | None
    methodology: str | None
    created_by_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
