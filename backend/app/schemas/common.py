"""
Schemas comuns para respostas de API.
Define estrutura padronizada para sucesso e erro.
"""
from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Detalhe de um erro."""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Resposta padrão de erro."""
    success: bool = Field(False)
    error: str
    details: List[ErrorDetail] = []
    request_id: Optional[str] = None


class SuccessResponse(BaseModel, Generic[T]):
    """Resposta padrão de sucesso (sem dados)."""
    success: bool = Field(True)
    message: Optional[str] = None
    request_id: Optional[str] = None


class DataResponse(BaseModel, Generic[T]):
    """Resposta padrão com dados."""
    success: bool = Field(True)
    data: T
    message: Optional[str] = None
    request_id: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Resposta padrão paginada."""
    success: bool = Field(True)
    data: List[T]
    total: int
    skip: int
    limit: int
    page: int = Field(default=1)
    total_pages: int = Field(default=1)
    request_id: Optional[str] = None


class StatusEnum(str):
    """Status comuns de recursos."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
