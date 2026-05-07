from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import Report, ReportSection
from app.schemas.report_section_draft import ReportSectionDraftRequest
from app.services.report_section_draft_service import generate_report_section_draft


@pytest.mark.asyncio
async def test_generate_report_section_draft_stores_mocked_ai_content(
    db_session: AsyncSession,
    sample_case,
):
    report, section = await _seed_report_section(db_session, sample_case.id, content="")

    response = await generate_report_section_draft(
        db_session,
        case_id=sample_case.id,
        report_section_id=section.id,
        payload=ReportSectionDraftRequest(
            context="Holerites e fichas financeiras foram conferidos.",
            instructions="Redigir de forma objetiva.",
        ),
    )

    assert response.report_section_id == section.id
    assert response.report_id == report.id
    assert response.is_ai_generated is True
    assert response.ai_provider == "mock"
    assert response.ai_model == "mock-report-section-draft-v1"
    assert "Minuta da seção" in response.content
    assert "Holerites e fichas financeiras" in response.content
    assert section.content == response.content
    assert section.is_ai_generated is True
    assert report.current_version == 2


@pytest.mark.asyncio
async def test_generate_report_section_draft_requires_overwrite_for_existing_content(
    db_session: AsyncSession,
    sample_case,
):
    _, section = await _seed_report_section(
        db_session,
        sample_case.id,
        content="Conteúdo manual existente.",
    )

    with pytest.raises(ValueError, match="Seção já possui conteúdo"):
        await generate_report_section_draft(
            db_session,
            case_id=sample_case.id,
            report_section_id=section.id,
            payload=ReportSectionDraftRequest(context="Contexto"),
        )


@pytest.mark.asyncio
async def test_report_section_draft_endpoint_generates_and_marks_ai_content(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_case,
    perito_token: str,
):
    report, section = await _seed_report_section(db_session, sample_case.id, content="")
    await db_session.commit()

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/report-sections/{section.id}/draft",
        json={
            "context": "Matriz de prova e evidências documentais disponíveis.",
            "instructions": "Usar linguagem técnica simples.",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report_section_id"] == section.id
    assert body["report_id"] == report.id
    assert body["is_ai_generated"] is True
    assert body["ai_provider"] == "mock"
    assert "Matriz de prova" in body["content"]

    refreshed = await db_session.get(ReportSection, section.id)
    assert refreshed is not None
    assert refreshed.is_ai_generated is True
    assert refreshed.ai_provider == "mock"
    assert refreshed.content == body["content"]


async def _seed_report_section(
    db_session: AsyncSession,
    case_id: str,
    content: str,
) -> tuple[Report, ReportSection]:
    report = Report(
        id=str(uuid.uuid4()),
        case_id=case_id,
        title="Laudo Pericial",
        report_type="trabalhista",
        status="rascunho",
        current_version=1,
    )
    section = ReportSection(
        id=str(uuid.uuid4()),
        report_id=report.id,
        title="Fundamentação Técnica",
        section_order=1,
        content=content,
        review_status="pendente",
    )
    db_session.add_all([report, section])
    await db_session.flush()
    return report, section
