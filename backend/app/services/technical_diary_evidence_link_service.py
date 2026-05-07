"""Service for linking technical diary entries to evidence."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evidence_item import EvidenceItem
from app.db.models.technical_diary_entry import TechnicalDiaryEntry
from app.db.models.technical_diary_evidence_link import TechnicalDiaryEvidenceLink
from app.schemas.technical_diary_evidence_link import (
    TechnicalDiaryEvidenceLinkResponse,
    TechnicalDiaryEvidenceListResponse,
)


async def link_evidence_to_technical_diary_entry(
    db: AsyncSession,
    case_id: str,
    technical_diary_entry_id: str,
    evidence_item_id: str,
    linked_by_id: str | None,
) -> TechnicalDiaryEvidenceLinkResponse:
    entry = await _get_entry_for_case(db, case_id, technical_diary_entry_id)
    evidence = await _get_evidence_for_case(db, case_id, evidence_item_id)

    existing = await db.scalar(
        select(TechnicalDiaryEvidenceLink).where(
            TechnicalDiaryEvidenceLink.technical_diary_entry_id == entry.id,
            TechnicalDiaryEvidenceLink.evidence_item_id == evidence.id,
        )
    )
    if existing:
        link = existing
    else:
        link = TechnicalDiaryEvidenceLink(
            id=str(uuid.uuid4()),
            technical_diary_entry_id=entry.id,
            evidence_item_id=evidence.id,
            linked_by_id=linked_by_id,
        )
        db.add(link)
        await db.flush()

    return _to_link_response(link)


async def list_evidence_for_technical_diary_entry(
    db: AsyncSession,
    case_id: str,
    technical_diary_entry_id: str,
) -> TechnicalDiaryEvidenceListResponse:
    entry = await _get_entry_for_case(db, case_id, technical_diary_entry_id)
    result = await db.execute(
        select(EvidenceItem)
        .join(
            TechnicalDiaryEvidenceLink,
            TechnicalDiaryEvidenceLink.evidence_item_id == EvidenceItem.id,
        )
        .where(TechnicalDiaryEvidenceLink.technical_diary_entry_id == entry.id)
        .order_by(EvidenceItem.created_at.desc())
    )
    items = result.scalars().all()
    return TechnicalDiaryEvidenceListResponse(
        technical_diary_entry_id=entry.id,
        total=len(items),
        items=items,
    )


async def _get_entry_for_case(
    db: AsyncSession,
    case_id: str,
    technical_diary_entry_id: str,
) -> TechnicalDiaryEntry:
    entry = await db.get(TechnicalDiaryEntry, technical_diary_entry_id)
    if not entry or entry.case_id != case_id:
        raise ValueError(f"Entrada de diário técnico {technical_diary_entry_id} não encontrada.")
    return entry


async def _get_evidence_for_case(
    db: AsyncSession,
    case_id: str,
    evidence_item_id: str,
) -> EvidenceItem:
    evidence = await db.get(EvidenceItem, evidence_item_id)
    if not evidence or evidence.case_id != case_id:
        raise ValueError(f"Evidência {evidence_item_id} não encontrada.")
    return evidence


def _to_link_response(link: TechnicalDiaryEvidenceLink) -> TechnicalDiaryEvidenceLinkResponse:
    return TechnicalDiaryEvidenceLinkResponse(
        id=link.id,
        technical_diary_entry_id=link.technical_diary_entry_id,
        evidence_item_id=link.evidence_item_id,
        linked_by_id=link.linked_by_id,
        created_at=link.created_at,
    )
