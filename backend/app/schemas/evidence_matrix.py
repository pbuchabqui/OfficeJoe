"""Schemas for evidence matrix (proof matrix)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class EvidenceMatrixCreateRequest(BaseModel):
    """Requisição para criar um item da matriz de prova."""

    disputed_fact: str = Field(..., min_length=1, max_length=1000, description="Fato controvertido")
    theme: str = Field(..., min_length=1, max_length=500, description="Tema")
    evidence_ids: list[str] = Field(
        ..., min_length=1, description="IDs das evidências vinculadas (mínimo 1)"
    )
    expert_procedure: str = Field(
        "", max_length=500, description="Procedimento pericial"
    )
    methodology_or_criteria: str = Field(
        "", description="Metodologia ou critério"
    )
    result_found: str = Field("", description="Resultado encontrado")
    technical_impact: str = Field("", description="Impacto técnico")

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, v: list[str]) -> list[str]:
        if len(v) == 0:
            raise ValueError("Deve estar vinculada pelo menos uma evidência")
        return v


class EvidenceMatrixUpdateRequest(BaseModel):
    """Requisição para atualizar um item da matriz de prova."""

    disputed_fact: str | None = Field(None, min_length=1, max_length=1000)
    theme: str | None = Field(None, min_length=1, max_length=500)
    evidence_ids: list[str] | None = Field(None, min_length=1)
    expert_procedure: str | None = Field(None, max_length=500)
    methodology_or_criteria: str | None = Field(None)
    result_found: str | None = Field(None)
    technical_impact: str | None = Field(None)
    status: str | None = Field(None, pattern="^(draft|published|archived)$")

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) == 0:
            raise ValueError("Deve estar vinculada pelo menos uma evidência")
        return v


class EvidenceMatrixResponse(BaseModel):
    """Resposta com dados de um item da matriz de prova."""

    id: str
    case_id: str
    disputed_fact: str
    theme: str
    evidence_ids: list[str]
    expert_procedure: str
    methodology_or_criteria: str
    result_found: str
    technical_impact: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvidenceMatrixPaginatedResponse(BaseModel):
    """Resposta paginada com itens da matriz de prova."""

    total: int = Field(..., description="Total de itens")
    limit: int = Field(..., description="Limite por página")
    offset: int = Field(..., description="Deslocamento")
    items: list[EvidenceMatrixResponse] = Field(..., description="Lista de itens")
