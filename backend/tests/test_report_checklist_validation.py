from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import Report
from app.schemas.report_checklist import ReportChecklistItemUpdateRequest
from app.services.report_checklist_service import (
    DEFAULT_REPORT_CHECKLIST_ITEMS,
    generate_report_checklist,
    update_report_checklist_item,
)
from app.services.report_checklist_validation_service import validate_report_checklist_for_export


@pytest.mark.asyncio
async def test_validate_report_checklist_blocks_incomplete_required_items(
    db_session: AsyncSession,
    sample_case,
):
    report = await _seed_report(db_session, sample_case.id)
    await generate_report_checklist(db_session, sample_case.id, report.id)

    validation = await validate_report_checklist_for_export(
        db_session,
        case_id=sample_case.id,
        report_id=report.id,
    )

    assert validation.can_export is False
    assert validation.blocking_count > 0
    assert "identificacao_processo" in {item.item_key for item in validation.blocking_items}


@pytest.mark.asyncio
async def test_validate_report_checklist_allows_export_when_required_items_resolved(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    report = await _seed_report(db_session, sample_case.id)
    checklist = await generate_report_checklist(db_session, sample_case.id, report.id)

    for item in checklist.items:
        await update_report_checklist_item(
            db_session,
            case_id=sample_case.id,
            report_id=report.id,
            item_id=item.id,
            payload=ReportChecklistItemUpdateRequest(status="completo"),
            updated_by_id=perito_user.id,
        )

    validation = await validate_report_checklist_for_export(
        db_session,
        case_id=sample_case.id,
        report_id=report.id,
    )

    assert validation.can_export is True
    assert validation.blocking_count == 0
    assert validation.blocking_items == []


@pytest.mark.asyncio
async def test_validate_report_checklist_treats_non_critical_annexes_as_non_blocking(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    report = await _seed_report(db_session, sample_case.id)
    checklist = await generate_report_checklist(db_session, sample_case.id, report.id)

    for item in checklist.items:
        if item.item_key in {"anexos", "apendices"}:
            continue
        await update_report_checklist_item(
            db_session,
            case_id=sample_case.id,
            report_id=report.id,
            item_id=item.id,
            payload=ReportChecklistItemUpdateRequest(status="completo"),
            updated_by_id=perito_user.id,
        )

    validation = await validate_report_checklist_for_export(
        db_session,
        case_id=sample_case.id,
        report_id=report.id,
    )

    assert validation.can_export is True
    assert {item_key for item_key, _ in DEFAULT_REPORT_CHECKLIST_ITEMS} >= {"anexos", "apendices"}


@pytest.mark.asyncio
async def test_report_checklist_export_validation_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_case,
    perito_token: str,
):
    report = await _seed_report(db_session, sample_case.id)
    await generate_report_checklist(db_session, sample_case.id, report.id)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/cases/{sample_case.id}/reports/{report.id}/checklist/export-validation",
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report_id"] == report.id
    assert body["can_export"] is False
    assert body["blocking_count"] > 0


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
