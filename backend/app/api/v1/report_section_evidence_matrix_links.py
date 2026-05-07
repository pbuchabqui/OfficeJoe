"""Endpoints for report section to evidence matrix links."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.report_section_evidence_matrix_link import (
    ReportSectionEvidenceMatrixLinkRequest,
    ReportSectionEvidenceMatrixLinkResponse,
    ReportSectionEvidenceMatrixUnlinkResponse,
)
from app.services.report_section_evidence_matrix_link_service import (
    link_matrix_item_to_report_section,
    unlink_matrix_item_from_report_section,
)

router = APIRouter(
    prefix="/cases/{case_id}/report-sections/{report_section_id}/evidence-matrix",
    tags=["Laudos"],
)


@router.post(
    "",
    response_model=ReportSectionEvidenceMatrixLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Vincular item da matriz de prova a uma seção do laudo",
)
async def link_report_section_matrix_item_endpoint(
    case_id: str,
    report_section_id: str,
    payload: ReportSectionEvidenceMatrixLinkRequest,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportSectionEvidenceMatrixLinkResponse:
    try:
        response = await link_matrix_item_to_report_section(
            db,
            case_id=case_id,
            report_section_id=report_section_id,
            evidence_matrix_item_id=payload.evidence_matrix_item_id,
            linked_by_id=current_user.id,
        )
        await db.commit()
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{evidence_matrix_item_id}",
    response_model=ReportSectionEvidenceMatrixUnlinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Desvincular item da matriz de prova de uma seção do laudo",
)
async def unlink_report_section_matrix_item_endpoint(
    case_id: str,
    report_section_id: str,
    evidence_matrix_item_id: str,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> ReportSectionEvidenceMatrixUnlinkResponse:
    try:
        response = await unlink_matrix_item_from_report_section(
            db,
            case_id=case_id,
            report_section_id=report_section_id,
            evidence_matrix_item_id=evidence_matrix_item_id,
        )
        await db.commit()
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
