"""Service for mocked AI report section draft generation."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import Report, ReportSection
from app.providers.report_section_draft_provider import MockReportSectionDraftProvider
from app.schemas.report_section_draft import ReportSectionDraftRequest, ReportSectionDraftResponse


async def generate_report_section_draft(
    db: AsyncSession,
    case_id: str,
    report_section_id: str,
    payload: ReportSectionDraftRequest,
    provider: MockReportSectionDraftProvider | None = None,
) -> ReportSectionDraftResponse:
    section, report = await _get_section_and_report_for_case(db, case_id, report_section_id)
    if section.content.strip() and not payload.overwrite_existing:
        raise ValueError("Seção já possui conteúdo. Use overwrite_existing=true para substituir.")

    provider = provider or MockReportSectionDraftProvider()
    draft = await provider.generate_section_draft(
        section_title=section.title,
        report_title=report.title,
        report_type=report.report_type,
        context=payload.context,
        instructions=payload.instructions,
    )

    section.content = draft.content
    section.is_ai_generated = True
    section.ai_provider = draft.provider
    section.ai_model = draft.model
    section.review_status = "pendente"
    report.current_version += 1
    await db.flush()

    return ReportSectionDraftResponse(
        report_section_id=section.id,
        report_id=report.id,
        title=section.title,
        content=section.content,
        is_ai_generated=section.is_ai_generated,
        ai_provider=section.ai_provider or "",
        ai_model=section.ai_model or "",
        review_status=section.review_status,
    )


async def _get_section_and_report_for_case(
    db: AsyncSession,
    case_id: str,
    report_section_id: str,
) -> tuple[ReportSection, Report]:
    result = await db.execute(
        select(ReportSection, Report)
        .join(Report, Report.id == ReportSection.report_id)
        .where(ReportSection.id == report_section_id, Report.case_id == case_id)
    )
    row = result.one_or_none()
    if not row:
        raise ValueError(f"Seção de laudo {report_section_id} não encontrada.")
    return row[0], row[1]
