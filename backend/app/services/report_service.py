"""Service for report and report section CRUD."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.report import Report, ReportSection
from app.schemas.report import (
    ReportCreateRequest,
    ReportSectionCreateRequest,
    ReportSectionUpdateRequest,
    ReportUpdateRequest,
)


async def create_report(
    db: AsyncSession,
    case_id: str,
    payload: ReportCreateRequest,
) -> Report:
    await _validate_case_exists(db, case_id)
    report = Report(
        case_id=case_id,
        title=payload.title,
        report_type=payload.report_type,
        status=payload.status,
        current_version=1,
    )
    db.add(report)
    await db.flush()
    return report


async def read_report(db: AsyncSession, report_id: str) -> Report:
    report = await db.get(Report, report_id)
    if not report:
        raise ValueError(f"Report {report_id} not found")
    return report


async def update_report(
    db: AsyncSession,
    report_id: str,
    case_id: str,
    payload: ReportUpdateRequest,
) -> Report:
    report = await read_report(db, report_id)
    _ensure_report_case(report, case_id)

    should_bump_version = False
    if payload.title is not None and payload.title != report.title:
        report.title = payload.title
        should_bump_version = True
    if payload.report_type is not None and payload.report_type != report.report_type:
        report.report_type = payload.report_type
        should_bump_version = True
    if payload.status is not None:
        report.status = payload.status

    if should_bump_version:
        _bump_version(report)
    await db.flush()
    return report


async def delete_report(db: AsyncSession, report_id: str) -> None:
    report = await read_report(db, report_id)
    await db.delete(report)
    await db.flush()


async def list_reports_by_case(
    db: AsyncSession,
    case_id: str,
    status: str | None = None,
    report_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Report], int]:
    await _validate_case_exists(db, case_id)
    filters = [Report.case_id == case_id]
    if status:
        filters.append(Report.status == status)
    if report_type:
        filters.append(Report.report_type == report_type)

    total = await db.scalar(select(func.count(Report.id)).where(*filters))
    result = await db.execute(
        select(Report)
        .where(*filters)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all(), total or 0


async def create_report_section(
    db: AsyncSession,
    case_id: str,
    report_id: str,
    payload: ReportSectionCreateRequest,
) -> ReportSection:
    report = await read_report(db, report_id)
    _ensure_report_case(report, case_id)
    section = ReportSection(
        report_id=report.id,
        title=payload.title,
        section_order=payload.section_order,
        content=payload.content,
        review_status=payload.review_status,
    )
    db.add(section)
    _bump_version(report)
    await db.flush()
    return section


async def list_report_sections(
    db: AsyncSession,
    case_id: str,
    report_id: str,
) -> list[ReportSection]:
    report = await read_report(db, report_id)
    _ensure_report_case(report, case_id)
    result = await db.execute(
        select(ReportSection)
        .where(ReportSection.report_id == report_id)
        .order_by(ReportSection.section_order)
    )
    return result.scalars().all()


async def read_report_section(
    db: AsyncSession,
    case_id: str,
    section_id: str,
) -> ReportSection:
    section = await db.get(ReportSection, section_id)
    if not section:
        raise ValueError(f"Report section {section_id} not found")
    report = await read_report(db, section.report_id)
    _ensure_report_case(report, case_id)
    return section


async def update_report_section(
    db: AsyncSession,
    case_id: str,
    section_id: str,
    payload: ReportSectionUpdateRequest,
) -> ReportSection:
    section = await read_report_section(db, case_id, section_id)
    report = await read_report(db, section.report_id)

    should_bump_version = False
    if payload.title is not None and payload.title != section.title:
        section.title = payload.title
        should_bump_version = True
    if payload.section_order is not None and payload.section_order != section.section_order:
        section.section_order = payload.section_order
        should_bump_version = True
    if payload.content is not None and payload.content != section.content:
        section.content = payload.content
        should_bump_version = True
    if payload.review_status is not None:
        section.review_status = payload.review_status

    if should_bump_version:
        _bump_version(report)
    await db.flush()
    return section


async def delete_report_section(
    db: AsyncSession,
    case_id: str,
    section_id: str,
) -> None:
    section = await read_report_section(db, case_id, section_id)
    report = await read_report(db, section.report_id)
    await db.delete(section)
    _bump_version(report)
    await db.flush()


async def _validate_case_exists(db: AsyncSession, case_id: str) -> Case:
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")
    return case


def _ensure_report_case(report: Report, case_id: str) -> None:
    if report.case_id != case_id:
        raise ValueError(f"Report {report.id} does not belong to case {case_id}")


def _bump_version(report: Report) -> None:
    report.current_version += 1
