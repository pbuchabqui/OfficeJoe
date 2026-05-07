"""Endpoints for report annexes and appendices."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.report_attachment import (
    ReportAttachmentCreateRequest,
    ReportAttachmentResponse,
)
from app.services.report_attachment_service import (
    create_report_attachment,
    list_report_attachments,
)

router = APIRouter(
    prefix="/cases/{case_id}/reports/{report_id}/attachments",
    tags=["Anexos e Apêndices"],
)


@router.post(
    "",
    response_model=ReportAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report_attachment_endpoint(
    case_id: str = Path(..., description="ID do processo"),
    report_id: str = Path(..., description="ID do laudo"),
    payload: ReportAttachmentCreateRequest = ...,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportAttachmentResponse:
    try:
        attachment = await create_report_attachment(db, case_id, report_id, payload)
        await db.commit()
        await db.refresh(attachment)
        return attachment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[ReportAttachmentResponse])
async def list_report_attachments_endpoint(
    case_id: str = Path(..., description="ID do processo"),
    report_id: str = Path(..., description="ID do laudo"),
    attachment_type: str | None = Query(None, pattern="^(anexo|apendice)$"),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> list[ReportAttachmentResponse]:
    try:
        return await list_report_attachments(db, case_id, report_id, attachment_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
