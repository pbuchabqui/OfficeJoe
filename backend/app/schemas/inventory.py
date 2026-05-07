from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class InventoryItemResponse(BaseModel):
    id: str
    document_id: str
    document_class: str
    start_page: int
    end_page: int
    page_count: int
    confidence_avg: Optional[float]
    generated_at: datetime

    model_config = {"from_attributes": True}


class InventoryResponse(BaseModel):
    document_id: str
    total_groups: int
    items: List[InventoryItemResponse]
