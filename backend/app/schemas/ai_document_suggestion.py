"""Schemas for AI document suggestion."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentSuggestion(BaseModel):
    """Suggested document from AI analysis."""

    document_type: str = Field(
        ..., description="Tipo de documento sugerido (e.g., Contrato, RG/CPF)"
    )
    description: str = Field(..., description="Descrição de por que o documento é necessário")
    priority: str = Field(
        ...,
        description="Prioridade da obtenção (baixa, média, alta, crítica)",
        pattern="^(baixa|média|alta|crítica)$",
    )
    estimated_impact: str = Field(
        ..., description="Impacto estimado se o documento não for obtido"
    )


class AIDocumentSuggestionRequest(BaseModel):
    """Request for AI document suggestions."""

    case_id: str = Field(..., description="ID do processo")
    context: str | None = Field(
        None,
        description="Contexto adicional para análise (e.g., assunto do processo, características especiais)",
        max_length=1000,
    )


class AIDocumentSuggestionResponse(BaseModel):
    """Response with AI-suggested documents."""

    case_id: str = Field(..., description="ID do processo")
    suggestions: list[DocumentSuggestion] = Field(
        ..., description="Lista de documentos sugeridos pela IA"
    )
    total_suggestions: int = Field(..., description="Total de sugestões geradas")
