"""Endpoints for document contradiction checks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.document_contradiction import (
    DocumentContradictionCompareRequest,
    DocumentContradictionComparisonResult,
)
from app.services.document_contradiction_service import (
    compare_holerite_financial_statement_rubrics,
)

router = APIRouter(prefix="/document-contradictions", tags=["Contradições Documentais"])


@router.post(
    "/compare",
    response_model=DocumentContradictionComparisonResult,
    status_code=status.HTTP_200_OK,
    summary="Executar comparação inicial de contradições documentais",
)
async def compare_document_contradictions_endpoint(
    payload: DocumentContradictionCompareRequest,
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> DocumentContradictionComparisonResult:
    """
    Executa a primeira regra de contradição documental:
    compara rubricas/valores entre holerite extraído e ficha financeira
    extraída para a mesma competência.
    """
    try:
        result = await compare_holerite_financial_statement_rubrics(
            db,
            case_id=payload.case_id,
            competencia=payload.competencia,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
