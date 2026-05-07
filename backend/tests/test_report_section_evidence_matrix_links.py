from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.evidence_item import EvidenceItem
from app.db.models.evidence_matrix_item import EvidenceMatrixItem
from app.db.models.report import Report, ReportSection
from app.db.models.report_section_evidence_matrix_link import ReportSectionEvidenceMatrixLink
from app.services.report_section_evidence_matrix_link_service import (
    link_matrix_item_to_report_section,
    unlink_matrix_item_from_report_section,
)


@pytest.mark.asyncio
async def test_link_matrix_item_warns_when_no_validated_evidence(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    section, matrix_item = await _seed_section_and_matrix_item(
        db_session,
        case_id=sample_case.id,
        with_validated_evidence=False,
    )

    response = await link_matrix_item_to_report_section(
        db_session,
        case_id=sample_case.id,
        report_section_id=section.id,
        evidence_matrix_item_id=matrix_item.id,
        linked_by_id=perito_user.id,
    )

    assert response.report_section_id == section.id
    assert response.evidence_matrix_item_id == matrix_item.id
    assert response.alert is not None
    assert response.alert.level == "atencao"


@pytest.mark.asyncio
async def test_link_matrix_item_has_no_alert_with_validated_evidence(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    section, matrix_item = await _seed_section_and_matrix_item(
        db_session,
        case_id=sample_case.id,
        with_validated_evidence=True,
    )

    response = await link_matrix_item_to_report_section(
        db_session,
        case_id=sample_case.id,
        report_section_id=section.id,
        evidence_matrix_item_id=matrix_item.id,
        linked_by_id=perito_user.id,
    )

    assert response.alert is None
    stored = (await db_session.execute(select(ReportSectionEvidenceMatrixLink))).scalars().all()
    assert len(stored) == 1


@pytest.mark.asyncio
async def test_unlink_matrix_item_from_report_section(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    section, matrix_item = await _seed_section_and_matrix_item(
        db_session,
        case_id=sample_case.id,
        with_validated_evidence=True,
    )
    await link_matrix_item_to_report_section(
        db_session,
        case_id=sample_case.id,
        report_section_id=section.id,
        evidence_matrix_item_id=matrix_item.id,
        linked_by_id=perito_user.id,
    )

    response = await unlink_matrix_item_from_report_section(
        db_session,
        case_id=sample_case.id,
        report_section_id=section.id,
        evidence_matrix_item_id=matrix_item.id,
    )

    assert response.removed is True
    remaining = (await db_session.execute(select(ReportSectionEvidenceMatrixLink))).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_report_section_matrix_link_endpoint_links_and_unlinks(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_case,
    perito_token: str,
):
    section, matrix_item = await _seed_section_and_matrix_item(
        db_session,
        case_id=sample_case.id,
        with_validated_evidence=False,
    )
    await db_session.commit()

    link_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/report-sections/{section.id}/evidence-matrix",
        json={"evidence_matrix_item_id": matrix_item.id},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert link_response.status_code == 201
    body = link_response.json()
    assert body["report_section_id"] == section.id
    assert body["evidence_matrix_item_id"] == matrix_item.id
    assert body["alert"]["level"] == "atencao"

    unlink_response = await client.delete(
        f"/api/v1/cases/{sample_case.id}/report-sections/{section.id}/evidence-matrix/{matrix_item.id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert unlink_response.status_code == 200
    assert unlink_response.json()["removed"] is True


async def _seed_section_and_matrix_item(
    db_session: AsyncSession,
    case_id: str,
    with_validated_evidence: bool,
) -> tuple[ReportSection, EvidenceMatrixItem]:
    report = Report(
        id=str(uuid.uuid4()),
        case_id=case_id,
        title="Laudo",
        report_type="trabalhista",
        status="rascunho",
        current_version=1,
    )
    section = ReportSection(
        id=str(uuid.uuid4()),
        report_id=report.id,
        title="Fundamentação",
        section_order=1,
        content="Conteúdo técnico.",
        review_status="pendente",
    )
    db_session.add_all([report, section])
    await db_session.flush()

    evidence_ids: list[str] = []
    if with_validated_evidence:
        doc = Document(
            id=str(uuid.uuid4()),
            case_id=case_id,
            original_filename="evidencia.pdf",
            display_name="evidencia.pdf",
            category="outro",
            sha256_hash="f" * 64,
            file_size_bytes=1024,
            mime_type="application/pdf",
            storage_bucket="test-bucket",
            storage_key="test/evidencia-matriz.pdf",
            status="uploaded",
            is_original_preserved=True,
        )
        evidence = EvidenceItem(
            id=str(uuid.uuid4()),
            case_id=case_id,
            document_id=doc.id,
            page_number=1,
            text_excerpt="Evidência validada da matriz",
            evidence_type="holerite",
            reliability_level=4,
            validated=True,
            validation_status="validated",
        )
        db_session.add_all([doc, evidence])
        await db_session.flush()
        evidence_ids.append(evidence.id)

    matrix_item = EvidenceMatrixItem(
        id=str(uuid.uuid4()),
        case_id=case_id,
        disputed_fact="Pagamento de verba salarial",
        theme="Remuneração",
        evidence_ids=evidence_ids,
        expert_procedure="Conferência documental",
        methodology_or_criteria="Comparação de documentos",
        result_found="Resultado técnico",
        technical_impact="Impacto técnico",
        status="published",
    )
    db_session.add(matrix_item)
    await db_session.flush()
    return section, matrix_item
