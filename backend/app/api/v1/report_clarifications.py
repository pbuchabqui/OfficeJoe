"""Endpoints for report clarifications."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.report_clarification import (
    ReportClarificationCreateRequest,
    ReportClarificationPaginatedResponse,
    ReportClarificationResponse,
    ReportClarificationUpdateRequest,
)
from app.services.report_clarification_service import (
    create_report_clarification,
    delete_report_clarification,
    list_report_clarifications_by_case,
    read_report_clarification,
    update_report_clarification,
)

router = APIRouter(prefix="/report-clarifications", tags=["Esclarecimentos"])


@router.post(
    "",
    response_model=ReportClarificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report_clarification_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    payload: ReportClarificationCreateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportClarificationResponse:
    try:
        clarification = await create_report_clarification(db, case_id, payload)
        await db.commit()
        await db.refresh(clarification)
        return clarification
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{clarification_id}",
    response_model=ReportClarificationResponse,
)
async def read_report_clarification_endpoint(
    clarification_id: str = Path(..., description="ID do esclarecimento"),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> ReportClarificationResponse:
    try:
        return await read_report_clarification(db, clarification_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{clarification_id}",
    response_model=ReportClarificationResponse,
)
async def update_report_clarification_endpoint(
    clarification_id: str = Path(..., description="ID do esclarecimento"),
    case_id: str = Query(..., description="ID do processo"),
    payload: ReportClarificationUpdateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportClarificationResponse:
    try:
        clarification = await update_report_clarification(
            db,
            clarification_id,
            case_id,
            payload,
        )
        await db.commit()
        await db.refresh(clarification)
        return clarification
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{clarification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_clarification_endpoint(
    clarification_id: str = Path(..., description="ID do esclarecimento"),
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await delete_report_clarification(db, clarification_id)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("", response_model=ReportClarificationPaginatedResponse)
async def list_report_clarifications_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    report_id: str | None = Query(None, description="Filtrar por laudo"),
    theme: str | None = Query(None, description="Filtrar por tema"),
    clarification_status: str | None = Query(None, description="Filtrar por status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> ReportClarificationPaginatedResponse:
    try:
        items, total = await list_report_clarifications_by_case(
            db,
            case_id=case_id,
            report_id=report_id,
            theme=theme,
            status=clarification_status,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ReportClarificationPaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )
