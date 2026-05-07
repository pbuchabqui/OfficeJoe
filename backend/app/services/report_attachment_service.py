"""Service for initial report annex and appendix control."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.calculation import Calculation, CalculationVersion
from app.db.models.document import Document
from app.db.models.report import Report
from app.db.models.report_attachment import ReportAttachment
from app.schemas.report_attachment import ReportAttachmentCreateRequest


async def create_report_attachment(
    db: AsyncSession,
    case_id: str,
    report_id: str,
    payload: ReportAttachmentCreateRequest,
) -> ReportAttachment:
    report = await _read_report_for_case(db, case_id, report_id)
    if payload.file_id:
        await _validate_file_belongs_to_case(db, case_id, payload.file_id)
    if payload.calculation_version_id:
        await _validate_calculation_version_belongs_to_case(
            db,
            case_id,
            payload.calculation_version_id,
        )

    next_number = await _next_number(db, report.id, payload.attachment_type)
    attachment = ReportAttachment(
        report_id=report.id,
        attachment_type=payload.attachment_type,
        number=next_number,
        title=payload.title,
        description=payload.description,
        file_id=payload.file_id,
        calculation_version_id=payload.calculation_version_id,
    )
    db.add(attachment)
    await db.flush()
    return attachment


async def list_report_attachments(
    db: AsyncSession,
    case_id: str,
    report_id: str,
    attachment_type: str | None = None,
) -> list[ReportAttachment]:
    await _read_report_for_case(db, case_id, report_id)
    filters = [ReportAttachment.report_id == report_id]
    if attachment_type:
        filters.append(ReportAttachment.attachment_type == attachment_type)
    result = await db.execute(
        select(ReportAttachment)
        .where(*filters)
        .order_by(ReportAttachment.attachment_type, ReportAttachment.number)
    )
    return result.scalars().all()


async def _read_report_for_case(db: AsyncSession, case_id: str, report_id: str) -> Report:
    report = await db.get(Report, report_id)
    if not report:
        raise ValueError(f"Report {report_id} not found")
    if report.case_id != case_id:
        raise ValueError(f"Report {report_id} does not belong to case {case_id}")
    return report


async def _validate_file_belongs_to_case(db: AsyncSession, case_id: str, file_id: str) -> None:
    document = await db.get(Document, file_id)
    if not document:
        raise ValueError(f"File {file_id} not found")
    if document.case_id != case_id:
        raise ValueError(f"File {file_id} does not belong to case {case_id}")


async def _validate_calculation_version_belongs_to_case(
    db: AsyncSession,
    case_id: str,
    calculation_version_id: str,
) -> None:
    result = await db.execute(
        select(CalculationVersion)
        .join(Calculation, Calculation.id == CalculationVersion.calculation_id)
        .where(
            CalculationVersion.id == calculation_version_id,
            Calculation.case_id == case_id,
        )
    )
    if not result.scalar_one_or_none():
        raise ValueError(
            f"Calculation version {calculation_version_id} not found for case {case_id}"
        )


async def _next_number(db: AsyncSession, report_id: str, attachment_type: str) -> int:
    current_max = await db.scalar(
        select(func.max(ReportAttachment.number)).where(
            ReportAttachment.report_id == report_id,
            ReportAttachment.attachment_type == attachment_type,
        )
    )
    return (current_max or 0) + 1
