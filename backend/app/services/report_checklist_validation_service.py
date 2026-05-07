"""Validation service for report checklist export readiness."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import Report
from app.db.models.report_checklist_item import ReportChecklistItem
from app.schemas.report_checklist import (
    ReportChecklistExportValidationItem,
    ReportChecklistExportValidationResponse,
)


CRITICAL_CHECKLIST_ITEM_KEYS = {
    "identificacao_processo",
    "objeto",
    "objetivo",
    "metodologia",
    "diligencias",
    "limitacoes",
    "quesitos",
    "conclusao",
    "assinatura",
}

RESOLVED_STATUSES = {"completo", "nao_aplicavel"}


async def validate_report_checklist_for_export(
    db: AsyncSession,
    case_id: str,
    report_id: str,
) -> ReportChecklistExportValidationResponse:
    report = await db.get(Report, report_id)
    if not report or report.case_id != case_id:
        raise ValueError(f"Report {report_id} not found")

    result = await db.execute(
        select(ReportChecklistItem)
        .where(ReportChecklistItem.report_id == report_id)
        .order_by(ReportChecklistItem.item_order)
    )
    items = result.scalars().all()
    by_key = {item.item_key: item for item in items}

    blocking_items: list[ReportChecklistExportValidationItem] = []
    for item_key in CRITICAL_CHECKLIST_ITEM_KEYS:
        item = by_key.get(item_key)
        if item is None:
            blocking_items.append(
                ReportChecklistExportValidationItem(
                    item_id="",
                    item_key=item_key,
                    title=_fallback_title(item_key),
                    status="ausente",
                    blocking=True,
                )
            )
            continue
        if item.status not in RESOLVED_STATUSES:
            blocking_items.append(
                ReportChecklistExportValidationItem(
                    item_id=item.id,
                    item_key=item.item_key,
                    title=item.title,
                    status=item.status,
                    blocking=True,
                )
            )

    can_export = len(blocking_items) == 0
    return ReportChecklistExportValidationResponse(
        report_id=report_id,
        can_export=can_export,
        blocking_count=len(blocking_items),
        blocking_items=blocking_items,
        message=(
            "Laudo apto para exportação quanto ao checklist normativo."
            if can_export
            else "Laudo possui itens obrigatórios incompletos no checklist normativo."
        ),
    )


def _fallback_title(item_key: str) -> str:
    return item_key.replace("_", " ").capitalize()
