"""Schemas for mocked AI report section draft generation."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ReportSectionDraftRequest(BaseModel):
    context: str | None = Field(None, description="Contexto técnico opcional para a minuta")
    instructions: str | None = Field(None, description="Instruções objetivas para a redação")
    overwrite_existing: bool = Field(
        False,
        description="Quando false, impede substituir conteúdo existente da seção.",
    )


class ReportSectionDraftResponse(BaseModel):
    report_section_id: str
    report_id: str
    title: str
    content: str
    is_ai_generated: bool
    ai_provider: str
    ai_model: str
    review_status: str
