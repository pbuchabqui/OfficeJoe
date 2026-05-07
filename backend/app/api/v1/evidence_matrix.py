"""Endpoints for evidence matrix (proof matrix)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.evidence_matrix import (
    EvidenceMatrixCreateRequest,
    EvidenceMatrixPaginatedResponse,
    EvidenceMatrixResponse,
    EvidenceMatrixUpdateRequest,
)
from app.services.evidence_matrix_service import (
    create_evidence_matrix,
    read_evidence_matrix,
    update_evidence_matrix,
    delete_evidence_matrix,
    list_evidence_matrix_by_case,
)

router = APIRouter(prefix="/evidence-matrix", tags=["Matriz de Prova"])


@router.post(
    "",
    response_model=EvidenceMatrixResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar item na matriz de prova",
)
async def create_matrix_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    payload: EvidenceMatrixCreateRequest = ...,
    current_user=Depends(require_permission("evidence_matrix:write")),
    db: AsyncSession = Depends(get_db),
) -> EvidenceMatrixResponse:
    """
    Cria um novo item na matriz de prova.

    Valida:
    - Processo existe
    - Todas as evidências existem e pertencem ao processo
    - Mínimo uma evidência está vinculada
    """
    try:
        matrix_item = await create_evidence_matrix(db, case_id, payload)
        await db.commit()
        await db.refresh(matrix_item)
        return matrix_item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{matrix_id}",
    response_model=EvidenceMatrixResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter item da matriz de prova",
)
async def read_matrix_endpoint(
    matrix_id: str = Path(..., description="ID do item da matriz"),
    current_user=Depends(require_permission("evidence_matrix:read")),
    db: AsyncSession = Depends(get_db),
) -> EvidenceMatrixResponse:
    """
    Obtém um item específico da matriz de prova.
    """
    try:
        matrix_item = await read_evidence_matrix(db, matrix_id)
        return matrix_item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{matrix_id}",
    response_model=EvidenceMatrixResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar item da matriz de prova",
)
async def update_matrix_endpoint(
    matrix_id: str = Path(..., description="ID do item da matriz"),
    case_id: str = Query(..., description="ID do processo"),
    payload: EvidenceMatrixUpdateRequest = ...,
    current_user=Depends(require_permission("evidence_matrix:write")),
    db: AsyncSession = Depends(get_db),
) -> EvidenceMatrixResponse:
    """
    Atualiza um item da matriz de prova.
    """
    try:
        matrix_item = await update_evidence_matrix(db, matrix_id, case_id, payload)
        await db.commit()
        await db.refresh(matrix_item)
        return matrix_item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{matrix_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar item da matriz de prova",
)
async def delete_matrix_endpoint(
    matrix_id: str = Path(..., description="ID do item da matriz"),
    current_user=Depends(require_permission("evidence_matrix:write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Deleta um item da matriz de prova.
    """
    try:
        await delete_evidence_matrix(db, matrix_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "",
    response_model=EvidenceMatrixPaginatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar matriz de prova por processo",
)
async def list_matrix_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission("evidence_matrix:read")),
    db: AsyncSession = Depends(get_db),
) -> EvidenceMatrixPaginatedResponse:
    """
    Lista todos os itens da matriz de prova de um processo (paginado).
    """
    items, total = await list_evidence_matrix_by_case(db, case_id, limit=limit, offset=offset)
    return EvidenceMatrixPaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )
