from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.evidence_item import EvidenceItem
from app.db.models.technical_diary_entry import TechnicalDiaryEntry
from app.db.models.technical_diary_evidence_link import TechnicalDiaryEvidenceLink
from app.services.technical_diary_evidence_link_service import (
    link_evidence_to_technical_diary_entry,
    list_evidence_for_technical_diary_entry,
)


@pytest.mark.asyncio
async def test_link_and_list_evidence_for_technical_diary_entry(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    entry, evidence = await _seed_entry_and_evidence(db_session, sample_case.id, perito_user.id)

    response = await link_evidence_to_technical_diary_entry(
        db_session,
        case_id=sample_case.id,
        technical_diary_entry_id=entry.id,
        evidence_item_id=evidence.id,
        linked_by_id=perito_user.id,
    )

    assert response.technical_diary_entry_id == entry.id
    assert response.evidence_item_id == evidence.id
    assert response.linked_by_id == perito_user.id

    list_response = await list_evidence_for_technical_diary_entry(
        db_session,
        case_id=sample_case.id,
        technical_diary_entry_id=entry.id,
    )
    assert list_response.total == 1
    assert list_response.items[0].id == evidence.id

    stored = (await db_session.execute(select(TechnicalDiaryEvidenceLink))).scalars().all()
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_link_evidence_to_technical_diary_entry_is_idempotent(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    entry, evidence = await _seed_entry_and_evidence(db_session, sample_case.id, perito_user.id)

    first = await link_evidence_to_technical_diary_entry(
        db_session,
        case_id=sample_case.id,
        technical_diary_entry_id=entry.id,
        evidence_item_id=evidence.id,
        linked_by_id=perito_user.id,
    )
    second = await link_evidence_to_technical_diary_entry(
        db_session,
        case_id=sample_case.id,
        technical_diary_entry_id=entry.id,
        evidence_item_id=evidence.id,
        linked_by_id=perito_user.id,
    )

    assert first.id == second.id
    stored = (await db_session.execute(select(TechnicalDiaryEvidenceLink))).scalars().all()
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_technical_diary_evidence_link_endpoint_links_and_lists(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_case,
    perito_user,
    perito_token: str,
):
    entry, evidence = await _seed_entry_and_evidence(db_session, sample_case.id, perito_user.id)
    await db_session.commit()

    link_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/technical-diary/{entry.id}/evidence",
        json={"evidence_item_id": evidence.id},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert link_response.status_code == 201
    assert link_response.json()["technical_diary_entry_id"] == entry.id
    assert link_response.json()["evidence_item_id"] == evidence.id

    list_response = await client.get(
        f"/api/v1/cases/{sample_case.id}/technical-diary/{entry.id}/evidence",
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["technical_diary_entry_id"] == entry.id
    assert body["total"] == 1
    assert body["items"][0]["id"] == evidence.id
    assert body["items"][0]["text_excerpt"] == "Evidência usada na decisão técnica"


async def _seed_entry_and_evidence(
    db_session: AsyncSession,
    case_id: str,
    user_id: str,
) -> tuple[TechnicalDiaryEntry, EvidenceItem]:
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=case_id,
        original_filename="evidencia.pdf",
        display_name="evidencia.pdf",
        category="outro",
        sha256_hash="e" * 64,
        file_size_bytes=1024,
        mime_type="application/pdf",
        storage_bucket="test-bucket",
        storage_key="test/evidencia-diario.pdf",
        status="uploaded",
        is_original_preserved=True,
    )
    entry = TechnicalDiaryEntry(
        id=str(uuid.uuid4()),
        case_id=case_id,
        entry_date=date(2026, 5, 7),
        responsible_user_id=user_id,
        decision_type="criterio_tecnico",
        description="Decisão técnica documentada.",
        technical_justification="Justificativa técnica baseada em evidência.",
        status="draft",
    )
    db_session.add_all([doc, entry])
    await db_session.flush()

    evidence = EvidenceItem(
        id=str(uuid.uuid4()),
        case_id=case_id,
        document_id=doc.id,
        page_number=1,
        text_excerpt="Evidência usada na decisão técnica",
        evidence_type="documento_contabil",
        reliability_level=4,
        validated=True,
        validation_status="validated",
    )
    db_session.add(evidence)
    await db_session.flush()
    return entry, evidence
