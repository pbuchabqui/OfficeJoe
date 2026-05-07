from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


DOCUMENT_CLASS_LABELS = [
    "holerite",
    "ficha financeira",
    "cartão ponto",
    "sentença",
    "acórdão",
    "decisão",
    "petição inicial",
    "contestação",
    "laudo",
    "parecer",
    "contrato",
    "extrato",
    "nota fiscal",
    "CCT",
    "ACT",
    "TRCT",
    "e-mail",
    "planilha",
    "documento ilegível",
    "outro",
]


class ClassificationAIResponse(BaseModel):
    document_class: str = Field(..., description="Classe documental prevista.")
    confidence: float = Field(..., ge=0, le=1)
    rationale: str | None = None


class PageClassificationResponse(BaseModel):
    id: str
    file_page_id: str
    file_id: str
    page_number: int
    document_class: str
    confidence: float
    rationale: str | None
    provider: str
    model_name: str
    raw_response: dict[str, Any] | None
    human_validated: bool
    validated_by: str | None
    validated_at: Any | None
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}

    def model_post_init(self, __context: Any) -> None:
        if not isinstance(self.created_at, str):
            object.__setattr__(self, "created_at", str(self.created_at))
        if not isinstance(self.updated_at, str):
            object.__setattr__(self, "updated_at", str(self.updated_at))
        if self.validated_at is not None and not isinstance(self.validated_at, str):
            object.__setattr__(self, "validated_at", str(self.validated_at))


class PageClassificationCorrectionRequest(BaseModel):
    document_class: str
