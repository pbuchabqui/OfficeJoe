from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class InventoryItemResponse(BaseModel):
    id: str
    document_id: str
    document_class: str
    start_page: int
    end_page: int
    page_count: int
    confidence_avg: Optional[float]
    generated_at: datetime
    custom_label: Optional[str]
    is_relevant: bool
    edited_by_id: Optional[str]
    edited_at: Optional[datetime]

    model_config = {"from_attributes": True}


class InventoryItemUpdateRequest(BaseModel):
    custom_label: Optional[str] = Field(None, max_length=255)
    document_class: Optional[str] = Field(None, max_length=100)
    start_page: Optional[int] = Field(None, ge=1)
    end_page: Optional[int] = Field(None, ge=1)
    is_relevant: Optional[bool] = None

    def has_changes(self) -> bool:
        return any(v is not None for v in [
            self.custom_label, self.document_class, self.start_page,
            self.end_page, self.is_relevant
        ])


class InventoryResponse(BaseModel):
    document_id: str
    total_groups: int
    items: List[InventoryItemResponse]

