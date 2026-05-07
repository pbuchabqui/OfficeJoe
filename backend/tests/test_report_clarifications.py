from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.report import ReportCreateRequest, ReportUpdateRequest
from app.schemas.report_clarification import (
    ReportClarificationCreateRequest,
    ReportClarificationUpdateRequest,
)
from app.services.report_clarification_service import (
    create_report_clarification,
    delete_report_clarification,
    list_report_clarifications_by_case,
    read_report_clarification,
    update_report_clarification,
)
from app.services.report_service import create_report, update_report


@pytest.mark.asyncio
async def test_create_read_update_delete_report_clarification(
    db_session: AsyncSession,
    sample_case,
):
    report = await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(title="Laudo", report_type="trabalhista"),
    )
    await update_report(
        db_session,
        report.id,
        sample_case.id,
        ReportUpdateRequest(title="Laudo revisado"),
    )

    clarification = await create_report_clarification(
        db_session,
        sample_case.id,
        ReportClarificationCreateRequest(
            report_id=report.id,
            request_text="Esclarecer critério de apuração das horas.",
            theme="horas extras",
            status="recebido",
        ),
    )

    assert clarification.case_id == sample_case.id
    assert clarification.report_id == report.id
    assert clarification.report_version == 2
    assert clarification.request_text.startswith("Esclarecer")

    read = await read_report_clarification(db_session, clarification.id)
    assert read.id == clarification.id

    updated = await update_report_clarification(
        db_session,
        clarification.id,
        sample_case.id,
        ReportClarificationUpdateRequest(
            status="respondido",
            preliminary_response="Resposta preliminar.",
            final_response="Resposta final.",
        ),
    )
    assert updated.status == "respondido"
    assert updated.preliminary_response == "Resposta preliminar."
    assert updated.final_response == "Resposta final."

    await delete_report_clarification(db_session, clarification.id)
    with pytest.raises(ValueError, match="Report clarification .* not found"):
        await read_report_clarification(db_session, clarification.id)


@pytest.mark.asyncio
async def test_list_report_clarifications_filters_by_report_theme_and_status(
    db_session: AsyncSession,
    sample_case,
):
    report = await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(title="Laudo", report_type="contabil"),
    )
    await create_report_clarification(
        db_session,
        sample_case.id,
        ReportClarificationCreateRequest(
            report_id=report.id,
            request_text="Esclarecer índice aplicado.",
            theme="indice",
            status="recebido",
        ),
    )
    await create_report_clarification(
        db_session,
        sample_case.id,
        ReportClarificationCreateRequest(
            report_id=report.id,
            request_text="Esclarecer documentos considerados.",
            theme="documentos",
            status="respondido",
        ),
    )

    all_items, total = await list_report_clarifications_by_case(db_session, sample_case.id)
    assert total == 2
    assert len(all_items) == 2

    by_report, report_total = await list_report_clarifications_by_case(
        db_session,
        sample_case.id,
        report_id=report.id,
    )
    assert report_total == 2
    assert {item.report_id for item in by_report} == {report.id}

    by_theme, theme_total = await list_report_clarifications_by_case(
        db_session,
        sample_case.id,
        theme="indice",
    )
    assert theme_total == 1
    assert by_theme[0].theme == "indice"

    by_status, status_total = await list_report_clarifications_by_case(
        db_session,
        sample_case.id,
        status="respondido",
    )
    assert status_total == 1
    assert by_status[0].status == "respondido"


@pytest.mark.asyncio
async def test_report_clarification_rejects_report_from_other_case(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    other_case = type(sample_case)(
        case_number="0000001-59.2024.5.02.0001",
        case_type=sample_case.case_type,
        title="Outro processo",
        status=sample_case.status,
        responsible_user_id=perito_user.id,
    )
    db_session.add(other_case)
    await db_session.flush()
    other_report = await create_report(
        db_session,
        other_case.id,
        ReportCreateRequest(title="Outro laudo", report_type="trabalhista"),
    )

    with pytest.raises(ValueError, match="does not belong to case"):
        await create_report_clarification(
            db_session,
            sample_case.id,
            ReportClarificationCreateRequest(
                report_id=other_report.id,
                request_text="Pedido fora do processo.",
                theme="competencia",
            ),
        )


@pytest.mark.asyncio
async def test_report_clarifications_endpoint_crud_and_filters(
    client: AsyncClient,
    sample_case,
    perito_token: str,
):
    report_response = await client.post(
        f"/api/v1/reports?case_id={sample_case.id}",
        json={"title": "Laudo", "report_type": "trabalhista"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert report_response.status_code == 201
    report_id = report_response.json()["id"]

    create_response = await client.post(
        f"/api/v1/report-clarifications?case_id={sample_case.id}",
        json={
            "report_id": report_id,
            "request_text": "Esclarecer conclusão.",
            "theme": "conclusao",
            "status": "recebido",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert create_response.status_code == 201
    clarification_id = create_response.json()["id"]
    assert create_response.json()["report_version"] == 1

    list_response = await client.get(
        f"/api/v1/report-clarifications?case_id={sample_case.id}&report_id={report_id}&theme=conclusao&clarification_status=recebido",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    update_response = await client.patch(
        f"/api/v1/report-clarifications/{clarification_id}?case_id={sample_case.id}",
        json={"status": "respondido", "final_response": "Resposta final registrada."},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "respondido"
    assert update_response.json()["final_response"] == "Resposta final registrada."

    delete_response = await client.delete(
        f"/api/v1/report-clarifications/{clarification_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/report-clarifications/{clarification_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert get_response.status_code == 404
