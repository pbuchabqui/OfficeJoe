from __future__ import annotations

from pydantic import BaseModel


class OCRSearchResult(BaseModel):
    file_id: str
    file_page_id: str
    page_number: int
    snippet: str
    score: float


class OCRSearchResponse(BaseModel):
    case_id: str
    query: str
    skip: int
    limit: int
    results: list[OCRSearchResult]
