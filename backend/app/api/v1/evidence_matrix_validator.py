"""Endpoints for evidence matrix validator."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.evidence_matrix_validator import ValidationResult
from app.services.evidence_matrix_validator_service import validate_matrix_item

router = APIRouter(prefix="/evidence-matrix", tags=["Validador de Matriz de Prova"])


@router.post(
    "/{matrix_id}/validate",
    response_model=ValidationResult,
    status_code=status.HTTP_200_OK,
    summary="Validar item da matriz de prova",
)
async def validate_matrix_item_endpoint(
    matrix_id: str = Path(..., description="ID do item da matriz de prova"),
    current_user=Depends(require_permission("evidence_matrix:read")),
    db: AsyncSession = Depends(get_db),
) -> ValidationResult:
    """
    Valida um item da matriz de prova para conclusividade.

    Regra: Se o item é conclusivo (resultado + impacto preenchidos, status=published),
    exige pelo menos 1 evidência validada.

    Retorna alertas com diferentes níveis:
    - informativo: Item válido
    - atenção: Evidências não validadas
    - crítico: Nenhuma evidência validada
    - bloqueante: Nenhuma evidência vinculada ou conclusão sem evidência
    """
    try:
        result = await validate_matrix_item(db, matrix_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
