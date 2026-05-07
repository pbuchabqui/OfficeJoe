"""Schemas for technical diary evidence links."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceResponse


class TechnicalDiaryEvidenceLinkRequest(BaseModel):
    evidence_item_id: str = Field(..., description="ID da evidência a vincular")


class TechnicalDiaryEvidenceLinkResponse(BaseModel):
    id: str
    technical_diary_entry_id: str
    evidence_item_id: str
    linked_by_id: str | None
    created_at: datetime


class TechnicalDiaryEvidenceListResponse(BaseModel):
    technical_diary_entry_id: str
    total: int
    items: list[EvidenceResponse]
