from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import Report
from app.db.models.report_checklist_item import ReportChecklistItem
from app.schemas.report_checklist import ReportChecklistItemUpdateRequest
from app.services.report_checklist_service import (
    DEFAULT_REPORT_CHECKLIST_ITEMS,
    generate_report_checklist,
    list_report_checklist,
    update_report_checklist_item,
)


@pytest.mark.asyncio
async def test_generate_report_checklist_creates_default_items_idempotently(
    db_session: AsyncSession,
    sample_case,
):
    report = await _seed_report(db_session, sample_case.id)

    first = await generate_report_checklist(db_session, sample_case.id, report.id)
    second = await generate_report_checklist(db_session, sample_case.id, report.id)

    assert first.total == len(DEFAULT_REPORT_CHECKLIST_ITEMS)
    assert second.total == len(DEFAULT_REPORT_CHECKLIST_ITEMS)
    assert [item.item_key for item in second.items] == [
        item_key for item_key, _ in DEFAULT_REPORT_CHECKLIST_ITEMS
    ]

    stored = (await db_session.execute(select(ReportChecklistItem))).scalars().all()
    assert len(stored) == len(DEFAULT_REPORT_CHECKLIST_ITEMS)


@pytest.mark.asyncio
async def test_update_report_checklist_item_status(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    report = await _seed_report(db_session, sample_case.id)
    checklist = await generate_report_checklist(db_session, sample_case.id, report.id)
    item = checklist.items[0]

    updated = await update_report_checklist_item(
        db_session,
        case_id=sample_case.id,
        report_id=report.id,
        item_id=item.id,
        payload=ReportChecklistItemUpdateRequest(
            status="completo",
            notes="Identificação conferida.",
        ),
        updated_by_id=perito_user.id,
    )

    assert updated.status == "completo"
    assert updated.notes == "Identificação conferida."
    assert updated.updated_by_id == perito_user.id


@pytest.mark.asyncio
async def test_list_report_checklist_returns_items_in_order(
    db_session: AsyncSession,
    sample_case,
):
    report = await _seed_report(db_session, sample_case.id)
    await generate_report_checklist(db_session, sample_case.id, report.id)

    response = await list_report_checklist(db_session, sample_case.id, report.id)

    assert response.total == 11
    assert response.items[0].item_key == "identificacao_processo"
    assert response.items[-1].item_key == "assinatura"


@pytest.mark.asyncio
async def test_report_checklist_endpoint_generate_list_and_update(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_case,
    perito_token: str,
):
    report = await _seed_report(db_session, sample_case.id)
    await db_session.commit()

    generate_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/reports/{report.id}/checklist/generate",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["total"] == 11
    item_id = body["items"][0]["id"]

    update_response = await client.patch(
        f"/api/v1/cases/{sample_case.id}/reports/{report.id}/checklist/items/{item_id}",
        json={"status": "nao_aplicavel", "notes": "Não se aplica ao caso."},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "nao_aplicavel"
    assert update_response.json()["notes"] == "Não se aplica ao caso."

    list_response = await client.get(
        f"/api/v1/cases/{sample_case.id}/reports/{report.id}/checklist",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 11


async def _seed_report(db_session: AsyncSession, case_id: str) -> Report:
    report = Report(
        id=str(uuid.uuid4()),
        case_id=case_id,
        title="Laudo Pericial",
        report_type="trabalhista",
        status="rascunho",
        current_version=1,
    )
    db_session.add(report)
    await db_session.flush()
    return report
