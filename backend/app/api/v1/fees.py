"""Endpoints for expert fee control."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.fee import (
    FeeCreateRequest,
    FeePaginatedResponse,
    FeeResponse,
    FeeUpdateRequest,
)
from app.services.fee_service import (
    create_fee,
    delete_fee,
    list_fees_by_case,
    read_fee,
    update_fee,
)

router = APIRouter(prefix="/fees", tags=["Honorários"])


@router.post("", response_model=FeeResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    payload: FeeCreateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> FeeResponse:
    try:
        fee = await create_fee(db, case_id, payload)
        await db.commit()
        await db.refresh(fee)
        return fee
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{fee_id}", response_model=FeeResponse)
async def read_fee_endpoint(
    fee_id: str = Path(..., description="ID dos honorários"),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> FeeResponse:
    try:
        return await read_fee(db, fee_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{fee_id}", response_model=FeeResponse)
async def update_fee_endpoint(
    fee_id: str = Path(..., description="ID dos honorários"),
    case_id: str = Query(..., description="ID do processo"),
    payload: FeeUpdateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> FeeResponse:
    try:
        fee = await update_fee(db, fee_id, case_id, payload)
        await db.commit()
        await db.refresh(fee)
        return fee
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{fee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fee_endpoint(
    fee_id: str = Path(..., description="ID dos honorários"),
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await delete_fee(db, fee_id)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("", response_model=FeePaginatedResponse)
async def list_fees_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    fee_status: str | None = Query(None, description="Filtrar por status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> FeePaginatedResponse:
    try:
        items, total = await list_fees_by_case(
            db,
            case_id=case_id,
            status=fee_status,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return FeePaginatedResponse(total=total, limit=limit, offset=offset, items=items)
