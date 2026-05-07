"""Endpoints for technical diary evidence links."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.technical_diary_evidence_link import (
    TechnicalDiaryEvidenceLinkRequest,
    TechnicalDiaryEvidenceLinkResponse,
    TechnicalDiaryEvidenceListResponse,
)
from app.services.technical_diary_evidence_link_service import (
    link_evidence_to_technical_diary_entry,
    list_evidence_for_technical_diary_entry,
)

router = APIRouter(
    prefix="/cases/{case_id}/technical-diary/{technical_diary_entry_id}/evidence",
    tags=["Diário Técnico"],
)


@router.post(
    "",
    response_model=TechnicalDiaryEvidenceLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Vincular evidência a uma decisão técnica",
)
async def link_technical_diary_evidence_endpoint(
    case_id: str,
    technical_diary_entry_id: str,
    payload: TechnicalDiaryEvidenceLinkRequest,
    current_user=Depends(require_permission("technical_limitation:write")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalDiaryEvidenceLinkResponse:
    try:
        response = await link_evidence_to_technical_diary_entry(
            db,
            case_id=case_id,
            technical_diary_entry_id=technical_diary_entry_id,
            evidence_item_id=payload.evidence_item_id,
            linked_by_id=current_user.id,
        )
        await db.commit()
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "",
    response_model=TechnicalDiaryEvidenceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar evidências vinculadas a uma decisão técnica",
)
async def list_technical_diary_evidence_endpoint(
    case_id: str,
    technical_diary_entry_id: str,
    current_user=Depends(require_permission("technical_limitation:read")),
    db: AsyncSession = Depends(get_db),
) -> TechnicalDiaryEvidenceListResponse:
    try:
        return await list_evidence_for_technical_diary_entry(
            db,
            case_id=case_id,
            technical_diary_entry_id=technical_diary_entry_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
