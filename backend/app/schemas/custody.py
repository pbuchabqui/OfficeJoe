from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.db.models.custody_event import CustodyEventType

_VALID_EVENT_TYPES = {e.value for e in CustodyEventType}


class CustodyEventResponse(BaseModel):
    id: str
    file_id: str
    event_type: str
    event_at: datetime
    actor_user_id: Optional[str]
    actor_ip: Optional[str]
    integrity_hash_verified: Optional[str]
    integrity_ok: Optional[bool]
    notes: Optional[str]
    model_config = {"from_attributes": True}


class CustodyChain(BaseModel):
    file_id: str
    total_events: int
    events: List[CustodyEventResponse]
