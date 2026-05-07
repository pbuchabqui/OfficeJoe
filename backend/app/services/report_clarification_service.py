"""Service for report clarification CRUD."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.report import Report
from app.db.models.report_clarification import ReportClarification
from app.schemas.report_clarification import (
    ReportClarificationCreateRequest,
    ReportClarificationUpdateRequest,
)


async def create_report_clarification(
    db: AsyncSession,
    case_id: str,
    payload: ReportClarificationCreateRequest,
) -> ReportClarification:
    report = await _read_report_for_case(db, case_id, payload.report_id)
    clarification = ReportClarification(
        case_id=case_id,
        report_id=report.id,
        report_version=report.current_version,
        request_text=payload.request_text,
        theme=payload.theme,
        status=payload.status,
        preliminary_response=payload.preliminary_response,
        final_response=payload.final_response,
    )
    db.add(clarification)
    await db.flush()
    return clarification


async def read_report_clarification(
    db: AsyncSession,
    clarification_id: str,
) -> ReportClarification:
    clarification = await db.get(ReportClarification, clarification_id)
    if not clarification:
        raise ValueError(f"Report clarification {clarification_id} not found")
    return clarification


async def update_report_clarification(
    db: AsyncSession,
    clarification_id: str,
    case_id: str,
    payload: ReportClarificationUpdateRequest,
) -> ReportClarification:
    clarification = await read_report_clarification(db, clarification_id)
    if clarification.case_id != case_id:
        raise ValueError(
            f"Report clarification {clarification_id} does not belong to case {case_id}"
        )

    if payload.request_text is not None:
        clarification.request_text = payload.request_text
    if payload.theme is not None:
        clarification.theme = payload.theme
    if payload.status is not None:
        clarification.status = payload.status
    if payload.preliminary_response is not None:
        clarification.preliminary_response = payload.preliminary_response
    if payload.final_response is not None:
        clarification.final_response = payload.final_response

    await db.flush()
    return clarification


async def delete_report_clarification(
    db: AsyncSession,
    clarification_id: str,
) -> None:
    clarification = await read_report_clarification(db, clarification_id)
    await db.delete(clarification)
    await db.flush()


async def list_report_clarifications_by_case(
    db: AsyncSession,
    case_id: str,
    report_id: str | None = None,
    theme: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ReportClarification], int]:
    await _validate_case_exists(db, case_id)
    filters = [ReportClarification.case_id == case_id]
    if report_id:
        filters.append(ReportClarification.report_id == report_id)
    if theme:
        filters.append(ReportClarification.theme == theme)
    if status:
        filters.append(ReportClarification.status == status)

    total = await db.scalar(select(func.count(ReportClarification.id)).where(*filters))
    result = await db.execute(
        select(ReportClarification)
        .where(*filters)
        .order_by(ReportClarification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all(), total or 0


async def _read_report_for_case(db: AsyncSession, case_id: str, report_id: str) -> Report:
    report = await db.get(Report, report_id)
    if not report:
        raise ValueError(f"Report {report_id} not found")
    if report.case_id != case_id:
        raise ValueError(f"Report {report_id} does not belong to case {case_id}")
    return report


async def _validate_case_exists(db: AsyncSession, case_id: str) -> Case:
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")
    return case
