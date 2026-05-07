"""Schemas for diligences (requests for additional information/documents)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DiligenceItemCreateRequest(BaseModel):
    """Requisição para criar um item de diligência."""

    requested_document: str = Field(..., min_length=1, max_length=500)
    period: str = Field(..., min_length=1, max_length=200)
    technical_justification: str = Field(..., min_length=1)


class DiligenceItemUpdateRequest(BaseModel):
    """Requisição para atualizar um item de diligência."""

    requested_document: str | None = Field(None, min_length=1, max_length=500)
    period: str | None = Field(None, min_length=1, max_length=200)
    technical_justification: str | None = Field(None, min_length=1)
    status: str | None = Field(None, pattern="^(pending|provided|rejected|withdrawn)$")


class DiligenceItemResponse(BaseModel):
    """Resposta com dados de um item de diligência."""

    id: str
    diligence_id: str
    requested_document: str
    period: str
    technical_justification: str
    status: str
    documento_recebido_id: str | None = None
    status_recebimento: str
    observacao_pendencia: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiligenceItemReceiptRequest(BaseModel):
    """Requisição para registrar recebimento de documento."""

    documento_recebido_id: str = Field(..., description="ID do documento recebido")
    status_recebimento: str = Field(
        ...,
        pattern="^(recebido|parcial|não_recebido)$",
        description="Status do recebimento"
    )
    observacao_pendencia: str | None = Field(None, max_length=2000)


class DiligenceCreateRequest(BaseModel):
    """Requisição para criar uma diligência."""

    number: str = Field(..., min_length=1, max_length=100)
    recipient: str = Field(..., min_length=1, max_length=500)
    deadline: datetime
    observations: str = Field("", max_length=2000)
    items: list[DiligenceItemCreateRequest] = Field(..., min_length=1)


class DiligenceUpdateRequest(BaseModel):
    """Requisição para atualizar uma diligência."""

    number: str | None = Field(None, min_length=1, max_length=100)
    recipient: str | None = Field(None, min_length=1, max_length=500)
    deadline: datetime | None = None
    observations: str | None = Field(None, max_length=2000)
    status: str | None = Field(None, pattern="^(draft|pending|completed|cancelled)$")


class DiligenceResponse(BaseModel):
    """Resposta com dados de uma diligência."""

    id: str
    case_id: str
    number: str
    recipient: str
    deadline: datetime
    status: str
    observations: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiligenceDetailedResponse(BaseModel):
    """Resposta detalhada com diligência e seus itens."""

    id: str
    case_id: str
    number: str
    recipient: str
    deadline: datetime
    status: str
    observations: str
    items: list[DiligenceItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiligencePaginatedResponse(BaseModel):
    """Resposta paginada com diligências."""

    total: int = Field(..., description="Total de diligências")
    limit: int = Field(..., description="Limite por página")
    offset: int = Field(..., description="Deslocamento")
    items: list[DiligenceResponse] = Field(..., description="Lista de diligências")
