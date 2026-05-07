from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.report import (
    ReportCreateRequest,
    ReportSectionCreateRequest,
    ReportSectionUpdateRequest,
    ReportUpdateRequest,
)
from app.services.report_service import (
    create_report,
    create_report_section,
    delete_report,
    delete_report_section,
    list_report_sections,
    list_reports_by_case,
    read_report,
    update_report,
    update_report_section,
)


@pytest.mark.asyncio
async def test_report_crud_and_simple_versioning(
    db_session: AsyncSession,
    sample_case,
):
    report = await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(
            title="Laudo Pericial Inicial",
            report_type="trabalhista",
            status="rascunho",
        ),
    )
    assert report.current_version == 1

    updated = await update_report(
        db_session,
        report.id,
        sample_case.id,
        ReportUpdateRequest(title="Laudo Pericial Revisado"),
    )
    assert updated.title == "Laudo Pericial Revisado"
    assert updated.current_version == 2

    status_only = await update_report(
        db_session,
        report.id,
        sample_case.id,
        ReportUpdateRequest(status="em_revisao"),
    )
    assert status_only.status == "em_revisao"
    assert status_only.current_version == 2

    read = await read_report(db_session, report.id)
    assert read.id == report.id

    await delete_report(db_session, report.id)
    with pytest.raises(ValueError, match="Report .* not found"):
        await read_report(db_session, report.id)


@pytest.mark.asyncio
async def test_report_sections_crud_and_versioning(
    db_session: AsyncSession,
    sample_case,
):
    report = await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(title="Laudo", report_type="trabalhista"),
    )
    section = await create_report_section(
        db_session,
        sample_case.id,
        report.id,
        ReportSectionCreateRequest(
            title="Introdução",
            section_order=1,
            content="Conteúdo inicial.",
        ),
    )
    assert section.report_id == report.id
    assert report.current_version == 2

    sections = await list_report_sections(db_session, sample_case.id, report.id)
    assert len(sections) == 1
    assert sections[0].title == "Introdução"

    updated = await update_report_section(
        db_session,
        sample_case.id,
        section.id,
        ReportSectionUpdateRequest(content="Conteúdo revisado."),
    )
    assert updated.content == "Conteúdo revisado."
    assert report.current_version == 3

    review_only = await update_report_section(
        db_session,
        sample_case.id,
        section.id,
        ReportSectionUpdateRequest(review_status="aprovada"),
    )
    assert review_only.review_status == "aprovada"
    assert report.current_version == 3

    await delete_report_section(db_session, sample_case.id, section.id)
    assert report.current_version == 4
    assert await list_report_sections(db_session, sample_case.id, report.id) == []


@pytest.mark.asyncio
async def test_list_reports_by_case_filters_status_and_type(
    db_session: AsyncSession,
    sample_case,
):
    await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(title="Laudo 1", report_type="trabalhista", status="rascunho"),
    )
    await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(title="Laudo 2", report_type="contabil", status="final"),
    )

    all_items, total = await list_reports_by_case(db_session, sample_case.id)
    assert total == 2
    assert len(all_items) == 2

    filtered_status, status_total = await list_reports_by_case(
        db_session,
        sample_case.id,
        status="final",
    )
    assert status_total == 1
    assert filtered_status[0].status == "final"

    filtered_type, type_total = await list_reports_by_case(
        db_session,
        sample_case.id,
        report_type="trabalhista",
    )
    assert type_total == 1
    assert filtered_type[0].report_type == "trabalhista"


@pytest.mark.asyncio
async def test_reports_endpoint_crud_sections_and_versioning(
    client: AsyncClient,
    sample_case,
    perito_token: str,
):
    create_response = await client.post(
        f"/api/v1/reports?case_id={sample_case.id}",
        json={"title": "Laudo", "report_type": "trabalhista", "status": "rascunho"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert create_response.status_code == 201
    report_id = create_response.json()["id"]
    assert create_response.json()["current_version"] == 1

    section_response = await client.post(
        f"/api/v1/reports/{report_id}/sections?case_id={sample_case.id}",
        json={"title": "Síntese", "section_order": 1, "content": "Texto inicial."},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert section_response.status_code == 201
    section_id = section_response.json()["id"]

    read_response = await client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert read_response.status_code == 200
    assert read_response.json()["current_version"] == 2
    assert len(read_response.json()["sections"]) == 1

    update_section_response = await client.patch(
        f"/api/v1/reports/sections/{section_id}?case_id={sample_case.id}",
        json={"content": "Texto revisado."},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert update_section_response.status_code == 200

    read_again = await client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert read_again.json()["current_version"] == 3

    delete_response = await client.delete(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert delete_response.status_code == 204
