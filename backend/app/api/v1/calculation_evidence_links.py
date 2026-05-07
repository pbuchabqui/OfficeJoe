"""Endpoints for linking calculation versions to evidence."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.calculation_evidence_link import (
    CalculationEvidenceLinkRequest,
    CalculationEvidenceLinkResponse,
    CalculationEvidenceUnlinkResponse,
)
from app.services.calculation_evidence_link_service import (
    link_evidence_to_calculation_version,
    unlink_evidence_from_calculation_version,
)

router = APIRouter(
    prefix="/cases/{case_id}/calculation-versions/{calculation_version_id}/evidence",
    tags=["Cálculos"],
)


@router.post(
    "",
    response_model=CalculationEvidenceLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Vincular evidência a uma versão de cálculo",
)
async def link_calculation_evidence_endpoint(
    case_id: str,
    calculation_version_id: str,
    payload: CalculationEvidenceLinkRequest,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> CalculationEvidenceLinkResponse:
    try:
        response = await link_evidence_to_calculation_version(
            db,
            case_id=case_id,
            calculation_version_id=calculation_version_id,
            evidence_item_id=payload.evidence_item_id,
            linked_by_id=current_user.id,
        )
        await db.commit()
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{evidence_item_id}",
    response_model=CalculationEvidenceUnlinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Desvincular evidência de uma versão de cálculo",
)
async def unlink_calculation_evidence_endpoint(
    case_id: str,
    calculation_version_id: str,
    evidence_item_id: str,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> CalculationEvidenceUnlinkResponse:
    try:
        response = await unlink_evidence_from_calculation_version(
            db,
            case_id=case_id,
            calculation_version_id=calculation_version_id,
            evidence_item_id=evidence_item_id,
        )
        await db.commit()
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
