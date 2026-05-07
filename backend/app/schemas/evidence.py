"""Schemas for evidence management."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.evidence import EvidenceType, ReliabilityLevel


class CoordinatesSchema(BaseModel):
    """Coordenadas opcionais de onde o texto foi extraído."""

    x: float = Field(..., description="Coordenada X em pixels")
    y: float = Field(..., description="Coordenada Y em pixels")
    width: float = Field(..., description="Largura do destaque em pixels")
    height: float = Field(..., description="Altura do destaque em pixels")


class EvidenceCreateRequest(BaseModel):
    """Requisição para criar uma evidência."""

    document_id: str = Field(..., description="ID do documento")
    page_number: int = Field(..., gt=0, description="Número da página")
    text_excerpt: str = Field(..., min_length=1, max_length=4000, description="Trecho de texto extraído")
    coordinates: CoordinatesSchema | None = Field(None, description="Coordenadas opcionais")
    evidence_type: EvidenceType = Field(..., description="Tipo de evidência")
    notes: str = Field("", max_length=2000, description="Observações")
    reliability_level: ReliabilityLevel = Field(
        ReliabilityLevel.MEDIA, description="Nível de confiabilidade (1-5)"
    )


class EvidenceResponse(BaseModel):
    """Resposta com dados de uma evidência."""

    id: str
    case_id: str
    document_id: str
    page_number: int
    text_excerpt: str
    coordinates: dict | None
    evidence_type: str
    notes: str
    reliability_level: int
    validated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvidencePaginatedResponse(BaseModel):
    """Resposta paginada com evidências."""

    total: int = Field(..., description="Total de evidências")
    limit: int = Field(..., description="Limite por página")
    offset: int = Field(..., description="Deslocamento")
    items: list[EvidenceResponse] = Field(..., description="Lista de evidências")
