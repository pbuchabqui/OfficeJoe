from __future__ import annotations

from typing import Any

from pydantic import BaseModel


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
    created_at: str

    model_config = {"from_attributes": True}

    def model_post_init(self, __context: Any) -> None:
        if not isinstance(self.created_at, str):
            object.__setattr__(self, "created_at", str(self.created_at))


class FilePagePreviewUrlResponse(BaseModel):
    url: str
    expires_in: int
    file_page_id: str
    file_id: str
    page_number: int
