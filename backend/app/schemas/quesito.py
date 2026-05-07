from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class QuesitoCreate(BaseModel):
    sequence_number: int
    origin: str = "juizo"
    question_text: str
    tema: Optional[str] = None
    tipo: Optional[str] = None


class QuesitoUpdate(BaseModel):
    question_text: Optional[str] = None
    status: Optional[str] = None
    tema: Optional[str] = None
    tipo: Optional[str] = None


class QuesitoImportItem(BaseModel):
    """Schema para importação de quesitos em lote via JSON."""
    sequence_number: int
    origin: str = "juizo"
    question_text: str
    tema: Optional[str] = None
    tipo: Optional[str] = None


class QuesitoImportRequest(BaseModel):
    """Request para batch import de quesitos."""
    quesitos: List[QuesitoImportItem]


class DocumentReference(BaseModel):
    document_id: str
    document_name: Optional[str] = None
    page_number: int
    excerpt: Optional[str] = None


class QuesitoAnswerCreate(BaseModel):
    answer_text: str
    document_references: Optional[List[DocumentReference]] = None


class QuesitoAnswerResponse(BaseModel):
    id: str
    quesito_id: str
    version: int
    answer_text: str
    document_references: Optional[List[Dict[str, Any]]]
    generated_by_ai: bool
    ai_model: Optional[str]
    ai_confidence: Optional[float]
    is_human_reviewed: bool
    review_note: Optional[str]

    model_config = {"from_attributes": True}


class QuesitoResponse(BaseModel):
    id: str
    case_id: str
    sequence_number: int
    origin: str
    status: str
    question_text: str
    tema: Optional[str] = None
    tipo: Optional[str] = None
    answers: List[QuesitoAnswerResponse] = []

    model_config = {"from_attributes": True}


class AIQuesitoRequest(BaseModel):
    quesito_id: str
    use_document_ids: Optional[List[str]] = None  # None = todos os documentos do processo
