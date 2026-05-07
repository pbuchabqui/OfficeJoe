"""Endpoints for evidence management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.evidence import EvidenceCreateRequest, EvidencePaginatedResponse, EvidenceResponse
from app.services.evidence_service import create_evidence, list_evidence_by_case

router = APIRouter(prefix="/evidence", tags=["Evidência"])


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar evidência em um processo",
)
async def create_evidence_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    payload: EvidenceCreateRequest = ...,
    current_user=Depends(require_permission("evidence:write")),
    db: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    """
    Cria uma nova evidência extraída manualmente de um documento.

    Valida:
    - Processo existe
    - Documento existe e pertence ao processo
    - Página existe no documento
    """
    try:
        evidence = await create_evidence(db, case_id, payload)
        await db.commit()
        await db.refresh(evidence)
        return evidence
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "",
    response_model=EvidencePaginatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar evidências de um processo",
)
async def list_evidence_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission("evidence:read")),
    db: AsyncSession = Depends(get_db),
) -> EvidencePaginatedResponse:
    """
    Lista todas as evidências de um processo (paginado).
    """
    items, total = await list_evidence_by_case(db, case_id, limit=limit, offset=offset)
    return EvidencePaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )
