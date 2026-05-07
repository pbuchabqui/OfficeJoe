"""Schemas for evidence matrix validator."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AlertLevel(str, Enum):
    """Níveis de alerta na validação."""

    INFORMATIVO = "informativo"
    ATENÇÃO = "atenção"
    CRÍTICO = "crítico"
    BLOQUEANTE = "bloqueante"


class Alert(BaseModel):
    """Um alerta gerado na validação."""

    level: AlertLevel = Field(..., description="Nível do alerta")
    message: str = Field(..., description="Mensagem do alerta")
    field: str | None = Field(None, description="Campo relacionado ao alerta")


class ValidationResult(BaseModel):
    """Resultado da validação de um item da matriz de prova."""

    matrix_id: str = Field(..., description="ID do item da matriz")
    is_valid: bool = Field(..., description="Indica se o item é válido")
    alerts: list[Alert] = Field(default_factory=list, description="Lista de alertas")
    summary: str = Field(..., description="Resumo da validação")
