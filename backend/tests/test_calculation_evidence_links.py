from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.calculation import Calculation, CalculationVersion
from app.db.models.calculation_evidence_link import CalculationEvidenceLink
from app.db.models.document import Document
from app.db.models.evidence_item import EvidenceItem
from app.services.calculation_evidence_link_service import (
    link_evidence_to_calculation_version,
    unlink_evidence_from_calculation_version,
)


@pytest.mark.asyncio
async def test_link_evidence_warns_when_evidence_is_not_validated(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    version, evidence = await _seed_version_and_evidence(
        db_session,
        case_id=sample_case.id,
        validated=False,
    )

    response = await link_evidence_to_calculation_version(
        db_session,
        case_id=sample_case.id,
        calculation_version_id=version.id,
        evidence_item_id=evidence.id,
        linked_by_id=perito_user.id,
    )

    assert response.calculation_version_id == version.id
    assert response.evidence_item_id == evidence.id
    assert response.alert is not None
    assert response.alert.level == "atencao"
    assert response.alert.evidence_item_id == evidence.id

    stored = (await db_session.execute(select(CalculationEvidenceLink))).scalars().all()
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_link_evidence_has_no_alert_when_evidence_is_validated(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    version, evidence = await _seed_version_and_evidence(
        db_session,
        case_id=sample_case.id,
        validated=True,
    )

    response = await link_evidence_to_calculation_version(
        db_session,
        case_id=sample_case.id,
        calculation_version_id=version.id,
        evidence_item_id=evidence.id,
        linked_by_id=perito_user.id,
    )

    assert response.alert is None


@pytest.mark.asyncio
async def test_unlink_evidence_from_calculation_version(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    version, evidence = await _seed_version_and_evidence(
        db_session,
        case_id=sample_case.id,
        validated=True,
    )
    await link_evidence_to_calculation_version(
        db_session,
        case_id=sample_case.id,
        calculation_version_id=version.id,
        evidence_item_id=evidence.id,
        linked_by_id=perito_user.id,
    )

    response = await unlink_evidence_from_calculation_version(
        db_session,
        case_id=sample_case.id,
        calculation_version_id=version.id,
        evidence_item_id=evidence.id,
    )

    assert response.removed is True
    remaining = (await db_session.execute(select(CalculationEvidenceLink))).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_calculation_evidence_link_endpoint_links_and_unlinks(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_case,
    perito_token: str,
):
    version, evidence = await _seed_version_and_evidence(
        db_session,
        case_id=sample_case.id,
        validated=False,
    )
    await db_session.commit()

    link_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/calculation-versions/{version.id}/evidence",
        json={"evidence_item_id": evidence.id},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert link_response.status_code == 201
    data = link_response.json()
    assert data["calculation_version_id"] == version.id
    assert data["evidence_item_id"] == evidence.id
    assert data["alert"]["level"] == "atencao"

    unlink_response = await client.delete(
        f"/api/v1/cases/{sample_case.id}/calculation-versions/{version.id}/evidence/{evidence.id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert unlink_response.status_code == 200
    assert unlink_response.json()["removed"] is True


async def _seed_version_and_evidence(
    db_session: AsyncSession,
    case_id: str,
    validated: bool,
) -> tuple[CalculationVersion, EvidenceItem]:
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=case_id,
        original_filename="evidencia.pdf",
        display_name="evidencia.pdf",
        category="outro",
        sha256_hash="c" * 64,
        file_size_bytes=1024,
        mime_type="application/pdf",
        storage_bucket="test-bucket",
        storage_key="test/evidencia.pdf",
        status="uploaded",
        is_original_preserved=True,
    )
    calculation = Calculation(
        id=str(uuid.uuid4()),
        case_id=case_id,
        calculation_type="liquidacao",
        description="Cálculo com evidências",
        status="rascunho",
    )
    db_session.add_all([doc, calculation])
    await db_session.flush()

    version = CalculationVersion(
        id=str(uuid.uuid4()),
        calculation_id=calculation.id,
        version_number=1,
        original_filename="calculo.xlsx",
        storage_bucket="test-bucket",
        storage_key=f"test/calculos/{uuid.uuid4()}/calculo.xlsx",
        sha256_hash="d" * 64,
        file_size_bytes=512,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        premises="Premissas",
        methodology="Metodologia",
    )
    evidence = EvidenceItem(
        id=str(uuid.uuid4()),
        case_id=case_id,
        document_id=doc.id,
        page_number=1,
        text_excerpt="Trecho usado no cálculo",
        evidence_type="holerite",
        reliability_level=4,
        validated=validated,
        validation_status="validated" if validated else "pending",
    )
    db_session.add_all([version, evidence])
    await db_session.flush()
    return version, evidence
