"""Endpoints for mocked AI report section drafts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.report_section_draft import ReportSectionDraftRequest, ReportSectionDraftResponse
from app.services.report_section_draft_service import generate_report_section_draft

router = APIRouter(
    prefix="/cases/{case_id}/report-sections/{report_section_id}/draft",
    tags=["Laudos"],
)


@router.post(
    "",
    response_model=ReportSectionDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar minuta mockada de seção de laudo",
)
async def generate_report_section_draft_endpoint(
    case_id: str,
    report_section_id: str,
    payload: ReportSectionDraftRequest,
    current_user=Depends(require_permission("ai:query")),
    db: AsyncSession = Depends(get_db),
) -> ReportSectionDraftResponse:
    try:
        response = await generate_report_section_draft(
            db,
            case_id=case_id,
            report_section_id=report_section_id,
            payload=payload,
        )
        await db.commit()
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
