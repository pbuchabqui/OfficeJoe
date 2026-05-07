"""Endpoints for technical limitations."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.technical_limitation import (
    TechnicalLimitationCreateRequest,
    TechnicalLimitationPaginatedResponse,
    TechnicalLimitationResponse,
    TechnicalLimitationUpdateRequest,
)
from app.services.technical_limitation_service import (
    create_technical_limitation,
    read_technical_limitation,
    update_technical_limitation,
    delete_technical_limitation,
    list_technical_limitations_by_case,
    create_limitation_from_diligence_item,
)

router = APIRouter(prefix="/technical-limitations", tags=["Limitações Técnicas"])


@router.post(
    "",
    response_model=TechnicalLimitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar limitação técnica",
)
async def create_limitation_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    payload: TechnicalLimitationCreateRequest = ...,
    current_user=Depends(require_permission("technical_limitation:write")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalLimitationResponse:
    """
    Cria uma nova limitação técnica para um processo.

    Valida:
    - Processo existe
    - Diligência e quesito (se fornecidos) pertencem ao processo
    """
    try:
        limitation = await create_technical_limitation(db, case_id, payload)
        await db.commit()
        await db.refresh(limitation)
        return limitation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{limitation_id}",
    response_model=TechnicalLimitationResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter limitação técnica",
)
async def read_limitation_endpoint(
    limitation_id: str = Path(..., description="ID da limitação"),
    current_user=Depends(require_permission("technical_limitation:read")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalLimitationResponse:
    """
    Obtém uma limitação técnica específica.
    """
    try:
        limitation = await read_technical_limitation(db, limitation_id)
        return limitation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{limitation_id}",
    response_model=TechnicalLimitationResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar limitação técnica",
)
async def update_limitation_endpoint(
    limitation_id: str = Path(..., description="ID da limitação"),
    case_id: str = Query(..., description="ID do processo"),
    payload: TechnicalLimitationUpdateRequest = ...,
    current_user=Depends(require_permission("technical_limitation:write")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalLimitationResponse:
    """
    Atualiza uma limitação técnica.
    """
    try:
        limitation = await update_technical_limitation(db, limitation_id, case_id, payload)
        await db.commit()
        await db.refresh(limitation)
        return limitation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{limitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar limitação técnica",
)
async def delete_limitation_endpoint(
    limitation_id: str = Path(..., description="ID da limitação"),
    current_user=Depends(require_permission("technical_limitation:write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Deleta uma limitação técnica.
    """
    try:
        await delete_technical_limitation(db, limitation_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "",
    response_model=TechnicalLimitationPaginatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar limitações técnicas",
)
async def list_limitations_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    criticality: str | None = Query(None, description="Filtrar por criticidade"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission("technical_limitation:read")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalLimitationPaginatedResponse:
    """
    Lista limitações técnicas de um processo com filtros opcionais.

    Filtros:
    - criticality: baixa, média, alta, crítica (opcional)
    """
    limitations, total = await list_technical_limitations_by_case(
        db, case_id, criticality=criticality, limit=limit, offset=offset
    )
    return TechnicalLimitationPaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=limitations,
    )


@router.post(
    "/from-diligence/{diligence_item_id}",
    response_model=TechnicalLimitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar limitação de diligência não atendida",
)
async def create_limitation_from_diligence_endpoint(
    diligence_item_id: str = Path(..., description="ID do item de diligência"),
    current_user=Depends(require_permission("technical_limitation:write")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalLimitationResponse:
    """
    Cria uma limitação técnica a partir de um item de diligência não atendido.

    Valida:
    - Item de diligência existe
    - Status do item é "não_recebido"
    - Registra entrada em log de auditoria
    """
    try:
        limitation = await create_limitation_from_diligence_item(
            db, diligence_item_id, current_user.id
        )
        await db.commit()
        await db.refresh(limitation)
        return limitation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
