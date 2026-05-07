"""Endpoints for report checklist items."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.report_checklist import (
    ReportChecklistExportValidationResponse,
    ReportChecklistItemResponse,
    ReportChecklistItemUpdateRequest,
    ReportChecklistResponse,
)
from app.services.report_checklist_service import (
    generate_report_checklist,
    list_report_checklist,
    update_report_checklist_item,
)
from app.services.report_checklist_validation_service import validate_report_checklist_for_export

router = APIRouter(
    prefix="/cases/{case_id}/reports/{report_id}/checklist",
    tags=["Laudos"],
)


@router.post(
    "/generate",
    response_model=ReportChecklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gerar checklist normativo inicial do laudo",
)
async def generate_report_checklist_endpoint(
    case_id: str,
    report_id: str,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportChecklistResponse:
    try:
        response = await generate_report_checklist(db, case_id, report_id)
        await db.commit()
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "",
    response_model=ReportChecklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar checklist normativo do laudo",
)
async def list_report_checklist_endpoint(
    case_id: str,
    report_id: str,
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> ReportChecklistResponse:
    try:
        return await list_report_checklist(db, case_id, report_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/items/{item_id}",
    response_model=ReportChecklistItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Marcar item do checklist",
)
async def update_report_checklist_item_endpoint(
    case_id: str,
    report_id: str,
    item_id: str,
    payload: ReportChecklistItemUpdateRequest,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportChecklistItemResponse:
    try:
        item = await update_report_checklist_item(
            db,
            case_id=case_id,
            report_id=report_id,
            item_id=item_id,
            payload=payload,
            updated_by_id=current_user.id,
        )
        await db.commit()
        await db.refresh(item)
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/export-validation",
    response_model=ReportChecklistExportValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validar se checklist permite exportação do laudo",
)
async def validate_report_checklist_export_endpoint(
    case_id: str,
    report_id: str,
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> ReportChecklistExportValidationResponse:
    try:
        return await validate_report_checklist_for_export(db, case_id, report_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
