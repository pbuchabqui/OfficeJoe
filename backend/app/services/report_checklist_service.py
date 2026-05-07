"""Service for initial normative report checklist."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import Report
from app.db.models.report_checklist_item import ReportChecklistItem
from app.schemas.report_checklist import ReportChecklistItemUpdateRequest, ReportChecklistResponse


DEFAULT_REPORT_CHECKLIST_ITEMS: tuple[tuple[str, str], ...] = (
    ("identificacao_processo", "Identificação do processo"),
    ("objeto", "Objeto"),
    ("objetivo", "Objetivo"),
    ("metodologia", "Metodologia"),
    ("diligencias", "Diligências"),
    ("limitacoes", "Limitações"),
    ("quesitos", "Quesitos"),
    ("conclusao", "Conclusão"),
    ("anexos", "Anexos"),
    ("apendices", "Apêndices"),
    ("assinatura", "Assinatura"),
)


async def generate_report_checklist(
    db: AsyncSession,
    case_id: str,
    report_id: str,
) -> ReportChecklistResponse:
    report = await _get_report_for_case(db, case_id, report_id)
    existing = await _list_items(db, report.id)
    existing_keys = {item.item_key for item in existing}

    for order, (item_key, title) in enumerate(DEFAULT_REPORT_CHECKLIST_ITEMS, start=1):
        if item_key in existing_keys:
            continue
        db.add(
            ReportChecklistItem(
                id=str(uuid.uuid4()),
                report_id=report.id,
                item_key=item_key,
                title=title,
                item_order=order,
                status="incompleto",
            )
        )

    await db.flush()
    items = await _list_items(db, report.id)
    return ReportChecklistResponse(report_id=report.id, total=len(items), items=items)


async def list_report_checklist(
    db: AsyncSession,
    case_id: str,
    report_id: str,
) -> ReportChecklistResponse:
    report = await _get_report_for_case(db, case_id, report_id)
    items = await _list_items(db, report.id)
    return ReportChecklistResponse(report_id=report.id, total=len(items), items=items)


async def update_report_checklist_item(
    db: AsyncSession,
    case_id: str,
    report_id: str,
    item_id: str,
    payload: ReportChecklistItemUpdateRequest,
    updated_by_id: str | None,
) -> ReportChecklistItem:
    await _get_report_for_case(db, case_id, report_id)
    item = await db.get(ReportChecklistItem, item_id)
    if not item or item.report_id != report_id:
        raise ValueError(f"Checklist item {item_id} not found")

    item.status = payload.status
    item.notes = payload.notes
    item.updated_by_id = updated_by_id
    await db.flush()
    return item


async def _get_report_for_case(db: AsyncSession, case_id: str, report_id: str) -> Report:
    report = await db.get(Report, report_id)
    if not report or report.case_id != case_id:
        raise ValueError(f"Report {report_id} not found")
    return report


async def _list_items(db: AsyncSession, report_id: str) -> list[ReportChecklistItem]:
    result = await db.execute(
        select(ReportChecklistItem)
        .where(ReportChecklistItem.report_id == report_id)
        .order_by(ReportChecklistItem.item_order)
    )
    return result.scalars().all()
