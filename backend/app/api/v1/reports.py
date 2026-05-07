"""Endpoints for reports and report sections."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.report import (
    ReportCreateRequest,
    ReportPaginatedResponse,
    ReportResponse,
    ReportSectionCreateRequest,
    ReportSectionResponse,
    ReportSectionUpdateRequest,
    ReportUpdateRequest,
    ReportWithSectionsResponse,
)
from app.services.report_service import (
    create_report,
    create_report_section,
    delete_report,
    delete_report_section,
    list_report_sections,
    list_reports_by_case,
    read_report,
    update_report,
    update_report_section,
)

router = APIRouter(prefix="/reports", tags=["Laudos"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    payload: ReportCreateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    try:
        report = await create_report(db, case_id, payload)
        await db.commit()
        await db.refresh(report)
        return report
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=ReportPaginatedResponse)
async def list_reports_endpoint(
    case_id: str = Query(..., description="ID do processo"),
    report_status: str | None = Query(None, description="Filtrar por status"),
    report_type: str | None = Query(None, description="Filtrar por tipo"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> ReportPaginatedResponse:
    try:
        items, total = await list_reports_by_case(
            db,
            case_id=case_id,
            status=report_status,
            report_type=report_type,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ReportPaginatedResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/{report_id}", response_model=ReportWithSectionsResponse)
async def read_report_endpoint(
    report_id: str = Path(..., description="ID do laudo"),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> ReportWithSectionsResponse:
    try:
        report = await read_report(db, report_id)
        sections = await list_report_sections(db, report.case_id, report.id)
        return ReportWithSectionsResponse(
            id=report.id,
            case_id=report.case_id,
            title=report.title,
            report_type=report.report_type,
            status=report.status,
            current_version=report.current_version,
            created_at=report.created_at,
            updated_at=report.updated_at,
            sections=[ReportSectionResponse.model_validate(section) for section in sections],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{report_id}", response_model=ReportResponse)
async def update_report_endpoint(
    report_id: str = Path(..., description="ID do laudo"),
    case_id: str = Query(..., description="ID do processo"),
    payload: ReportUpdateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    try:
        report = await update_report(db, report_id, case_id, payload)
        await db.commit()
        await db.refresh(report)
        return report
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_endpoint(
    report_id: str = Path(..., description="ID do laudo"),
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await delete_report(db, report_id)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{report_id}/sections",
    response_model=ReportSectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report_section_endpoint(
    report_id: str = Path(..., description="ID do laudo"),
    case_id: str = Query(..., description="ID do processo"),
    payload: ReportSectionCreateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportSectionResponse:
    try:
        section = await create_report_section(db, case_id, report_id, payload)
        await db.commit()
        await db.refresh(section)
        return section
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{report_id}/sections", response_model=list[ReportSectionResponse])
async def list_report_sections_endpoint(
    report_id: str = Path(..., description="ID do laudo"),
    case_id: str = Query(..., description="ID do processo"),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> list[ReportSectionResponse]:
    try:
        return await list_report_sections(db, case_id, report_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/sections/{section_id}", response_model=ReportSectionResponse)
async def update_report_section_endpoint(
    section_id: str = Path(..., description="ID da seção"),
    case_id: str = Query(..., description="ID do processo"),
    payload: ReportSectionUpdateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportSectionResponse:
    try:
        section = await update_report_section(db, case_id, section_id, payload)
        await db.commit()
        await db.refresh(section)
        return section
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_section_endpoint(
    section_id: str = Path(..., description="ID da seção"),
    case_id: str = Query(..., description="ID do processo"),
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await delete_report_section(db, case_id, section_id)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
