from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_serializer


class ProcessingJobResponse(BaseModel):
    id: str
    document_id: str
    case_id: str
    job_type: str
    status: str
    celery_task_id: Optional[str]
    error_message: Optional[str]
    result: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()
