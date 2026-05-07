"""Schemas for report annexes and appendices."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ReportAttachmentCreateRequest(BaseModel):
    attachment_type: str = Field(..., pattern="^(anexo|apendice)$")
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    file_id: str | None = None
    calculation_version_id: str | None = None

    @model_validator(mode="after")
    def validate_single_optional_source(self) -> "ReportAttachmentCreateRequest":
        if self.file_id and self.calculation_version_id:
            raise ValueError("Informe arquivo ou cálculo, não ambos")
        return self


class ReportAttachmentResponse(BaseModel):
    id: str
    report_id: str
    attachment_type: str
    number: int
    title: str
    description: str | None
    file_id: str | None
    calculation_version_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
