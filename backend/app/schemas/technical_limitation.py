"""Schemas for technical limitations."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TechnicalLimitationCreateRequest(BaseModel):
    """Requisição para criar uma limitação técnica."""

    type: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    technical_impact: str = Field(..., min_length=1)
    criticality: str = Field(
        ...,
        pattern="^(baixa|média|alta|crítica)$",
        description="Nível de criticidade"
    )
    diligence_id: str | None = Field(None, description="ID da diligência relacionada")
    quesito_id: str | None = Field(None, description="ID do quesito relacionado")


class TechnicalLimitationUpdateRequest(BaseModel):
    """Requisição para atualizar uma limitação técnica."""

    type: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1)
    technical_impact: str | None = Field(None, min_length=1)
    criticality: str | None = Field(None, pattern="^(baixa|média|alta|crítica)$")
    status: str | None = Field(None, pattern="^(draft|active|resolved|archived)$")
    diligence_id: str | None = Field(None)
    quesito_id: str | None = Field(None)


class TechnicalLimitationResponse(BaseModel):
    """Resposta com dados de uma limitação técnica."""

    id: str
    case_id: str
    type: str
    description: str
    technical_impact: str
    criticality: str
    status: str
    diligence_id: str | None = None
    quesito_id: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TechnicalLimitationPaginatedResponse(BaseModel):
    """Resposta paginada com limitações técnicas."""

    total: int = Field(..., description="Total de limitações")
    limit: int = Field(..., description="Limite por página")
    offset: int = Field(..., description="Deslocamento")
    items: list[TechnicalLimitationResponse] = Field(..., description="Lista de limitações")
