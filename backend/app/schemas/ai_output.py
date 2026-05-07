from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AISource(BaseModel):
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    page_number: Optional[int] = None
    excerpt: Optional[str] = None
    confidence: Optional[float] = None


class AIOutputResponse(BaseModel):
    id: str
    output_type: str
    ai_provider: str
    ai_model: str
    output_text: Optional[str]
    structured_output: Optional[Dict[str, Any]]
    sources: Optional[List[Dict[str, Any]]]
    overall_confidence: Optional[float]
    review_status: str
    has_documental_basis: bool
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]

    model_config = {"from_attributes": True}


class AIReviewUpdate(BaseModel):
    review_status: str  # approved | rejected | partially_approved
    review_note: Optional[str] = None


class SemanticSearchRequest(BaseModel):
    query: str
    case_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    top_k: int = 10


class SemanticSearchResult(BaseModel):
    chunk_text: str
    page_number: int
    document_id: str
    document_name: Optional[str]
    similarity: float
    page_id: str
