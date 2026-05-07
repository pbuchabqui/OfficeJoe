from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PageTextBlockResponse(BaseModel):
    id: str
    file_page_id: str
    file_id: str
    page_number: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float | None
    source: str

    model_config = {"from_attributes": True}


class FilePageOCRTextResponse(BaseModel):
    file_page_id: str
    file_id: str
    page_number: int
    status_ocr: str
    full_text: str
    blocks: list[PageTextBlockResponse]

    model_config = {"from_attributes": True}

    def model_post_init(self, __context: Any) -> None:
        self.full_text = self.full_text.strip()
