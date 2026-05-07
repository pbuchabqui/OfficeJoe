"""Endpoints for technical diary entries."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.technical_diary import (
    TechnicalDiaryEntryCreateRequest,
    TechnicalDiaryEntryPaginatedResponse,
    TechnicalDiaryEntryResponse,
    TechnicalDiaryEntryUpdateRequest,
)
from app.services.technical_diary_service import (
    create_technical_diary_entry,
    delete_technical_diary_entry,
    list_technical_diary_entries_by_case,
    read_technical_diary_entry,
    update_technical_diary_entry,
)

router = APIRouter(prefix="/technical-diary", tags=["Diário Técnico"])


@router.post(
    "",
    response_model=TechnicalDiaryEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar entrada de diário técnico",
)
async def create_technical_diary_entry_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    payload: TechnicalDiaryEntryCreateRequest = ...,
    current_user=Depends(require_permission("technical_limitation:write")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalDiaryEntryResponse:
    try:
        entry = await create_technical_diary_entry(db, case_id, payload)
        await db.commit()
        await db.refresh(entry)
        return entry
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{entry_id}",
    response_model=TechnicalDiaryEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter entrada de diário técnico",
)
async def read_technical_diary_entry_endpoint(
    entry_id: str = Path(..., description="ID da entrada"),
    current_user=Depends(require_permission("technical_limitation:read")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalDiaryEntryResponse:
    try:
        return await read_technical_diary_entry(db, entry_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{entry_id}",
    response_model=TechnicalDiaryEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar entrada de diário técnico",
)
async def update_technical_diary_entry_endpoint(
    entry_id: str = Path(..., description="ID da entrada"),
    case_id: str = Query(..., description="ID do processo"),
    payload: TechnicalDiaryEntryUpdateRequest = ...,
    current_user=Depends(require_permission("technical_limitation:write")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalDiaryEntryResponse:
    try:
        entry = await update_technical_diary_entry(db, entry_id, case_id, payload)
        await db.commit()
        await db.refresh(entry)
        return entry
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir entrada de diário técnico",
)
async def delete_technical_diary_entry_endpoint(
    entry_id: str = Path(..., description="ID da entrada"),
    current_user=Depends(require_permission("technical_limitation:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await delete_technical_diary_entry(db, entry_id)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "",
    response_model=TechnicalDiaryEntryPaginatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar entradas de diário técnico",
)
async def list_technical_diary_entries_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    decision_type: str | None = Query(None, description="Filtrar por tipo de decisão"),
    entry_status: str | None = Query(None, description="Filtrar por status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission("technical_limitation:read")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalDiaryEntryPaginatedResponse:
    try:
        items, total = await list_technical_diary_entries_by_case(
            db,
            case_id=case_id,
            decision_type=decision_type,
            status=entry_status,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return TechnicalDiaryEntryPaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )
