"""Schemas para busca semântica."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Requisição de busca semântica."""

    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=50)
    min_similarity: float = Field(0.3, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    """Um resultado de busca semântica."""

    chunk_id: str
    document_id: str
    page_number: int
    text: str
    similarity: float = Field(..., ge=0.0, le=1.0)

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    """Resposta de busca semântica."""

    query: str
    total_results: int
    results: List[SearchResultItem]
