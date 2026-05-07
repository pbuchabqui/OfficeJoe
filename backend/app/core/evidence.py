"""Enums for evidence management."""
from enum import Enum


class EvidenceType(str, Enum):
    """Tipos de evidência que podem ser criados."""

    CONTRATO = "contrato"
    DEPOIMENTO = "depoimento"
    DOCUMENTO_FINANCEIRO = "documento_financeiro"
    HOLERITE = "holerite"
    NOTA_FISCAL = "nota_fiscal"
    EXTRATO_BANCARIO = "extrato_bancario"
    EMAIL = "email"
    MENSAGEM = "mensagem"
    FOTO = "foto"
    AUDIO = "audio"
    OUTRO = "outro"


class ReliabilityLevel(int, Enum):
    """Nível de confiabilidade da evidência (1-5)."""

    MUITO_BAIXA = 1
    BAIXA = 2
    MEDIA = 3
    ALTA = 4
    MUITO_ALTA = 5
