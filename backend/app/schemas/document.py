from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    case_id: str
    original_filename: str
    display_name: Optional[str]
    category: str
    sha256_hash: str
    file_size_bytes: int
    total_pages: Optional[int]
    pdf_is_valid: Optional[bool]
    has_native_text: Optional[bool]
    status: str
    ocr_engine_used: Optional[str]
    ocr_avg_confidence: Optional[str]
    error_message: Optional[str]
    is_original_preserved: bool
    processing_job_id: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}

    def model_post_init(self, __context: Any) -> None:
        if hasattr(self, "created_at") and not isinstance(self.created_at, str):
            object.__setattr__(self, "created_at", str(self.created_at))


class DocumentIntegrityResponse(BaseModel):
    document_id: str
    sha256_hash: str
    integrity_ok: bool
    filename: str


class PageResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    raw_text: Optional[str]
    ocr_engine: Optional[str]
    ocr_confidence: Optional[float]
    has_text_layer: bool
    is_image_only: bool
    width_pt: Optional[float]
    height_pt: Optional[float]
    text_blocks: Optional[List[Dict[str, Any]]]
    tables_detected: Optional[List[Dict[str, Any]]]

    model_config = {"from_attributes": True}


class ExtractionResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    extraction_type: str
    bbox_x0: Optional[float]
    bbox_y0: Optional[float]
    bbox_x1: Optional[float]
    bbox_y1: Optional[float]
    raw_value: Optional[str]
    normalized_value: Optional[str]
    structured_data: Optional[Dict[str, Any]]
    confidence: Optional[float]
    is_reviewed: bool
    extractor_name: Optional[str]

    model_config = {"from_attributes": True}
