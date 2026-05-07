from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ProcessingJobResponse(BaseModel):
    id: str
    document_id: str
    case_id: str
    job_type: str
    status: str
    celery_task_id: Optional[str]
    error_message: Optional[str]
    result: Optional[dict[str, Any]]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    def model_post_init(self, __context: Any) -> None:
        if not isinstance(self.created_at, str):
            object.__setattr__(self, "created_at", str(self.created_at))
        if not isinstance(self.updated_at, str):
            object.__setattr__(self, "updated_at", str(self.updated_at))
