from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_serializer


class FilePageResponse(BaseModel):
    id: str
    file_id: str
    page_number: int
    width: float
    height: float
    status_ocr: str
    status_preview: str
    preview_storage_key: str | None
    average_confidence: float | None
    low_confidence: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()


class FilePagePreviewUrlResponse(BaseModel):
    url: str
    expires_in: int
    file_page_id: str
    file_id: str
    page_number: int
