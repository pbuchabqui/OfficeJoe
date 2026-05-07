"""Service for linking report sections to evidence matrix items."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evidence_item import EvidenceItem
from app.db.models.evidence_matrix_item import EvidenceMatrixItem
from app.db.models.report import Report, ReportSection
from app.db.models.report_section_evidence_matrix_link import ReportSectionEvidenceMatrixLink
from app.schemas.report_section_evidence_matrix_link import (
    ReportSectionEvidenceMatrixAlert,
    ReportSectionEvidenceMatrixLinkResponse,
    ReportSectionEvidenceMatrixUnlinkResponse,
)


async def link_matrix_item_to_report_section(
    db: AsyncSession,
    case_id: str,
    report_section_id: str,
    evidence_matrix_item_id: str,
    linked_by_id: str | None,
) -> ReportSectionEvidenceMatrixLinkResponse:
    section = await _get_section_for_case(db, case_id, report_section_id)
    matrix_item = await _get_matrix_item_for_case(db, case_id, evidence_matrix_item_id)

    existing = await db.scalar(
        select(ReportSectionEvidenceMatrixLink).where(
            ReportSectionEvidenceMatrixLink.report_section_id == section.id,
            ReportSectionEvidenceMatrixLink.evidence_matrix_item_id == matrix_item.id,
        )
    )
    if existing:
        link = existing
    else:
        link = ReportSectionEvidenceMatrixLink(
            id=str(uuid.uuid4()),
            report_section_id=section.id,
            evidence_matrix_item_id=matrix_item.id,
            linked_by_id=linked_by_id,
        )
        db.add(link)
        await db.flush()

    return _to_link_response(link, await _matrix_validation_alert(db, matrix_item))


async def unlink_matrix_item_from_report_section(
    db: AsyncSession,
    case_id: str,
    report_section_id: str,
    evidence_matrix_item_id: str,
) -> ReportSectionEvidenceMatrixUnlinkResponse:
    await _get_section_for_case(db, case_id, report_section_id)
    await _get_matrix_item_for_case(db, case_id, evidence_matrix_item_id)

    result = await db.execute(
        delete(ReportSectionEvidenceMatrixLink).where(
            ReportSectionEvidenceMatrixLink.report_section_id == report_section_id,
            ReportSectionEvidenceMatrixLink.evidence_matrix_item_id == evidence_matrix_item_id,
        )
    )
    return ReportSectionEvidenceMatrixUnlinkResponse(
        report_section_id=report_section_id,
        evidence_matrix_item_id=evidence_matrix_item_id,
        removed=(result.rowcount or 0) > 0,
    )


async def _get_section_for_case(
    db: AsyncSession,
    case_id: str,
    report_section_id: str,
) -> ReportSection:
    result = await db.execute(
        select(ReportSection)
        .join(Report, Report.id == ReportSection.report_id)
        .where(ReportSection.id == report_section_id, Report.case_id == case_id)
    )
    section = result.scalar_one_or_none()
    if not section:
        raise ValueError(f"Seção de laudo {report_section_id} não encontrada.")
    return section


async def _get_matrix_item_for_case(
    db: AsyncSession,
    case_id: str,
    evidence_matrix_item_id: str,
) -> EvidenceMatrixItem:
    matrix_item = await db.get(EvidenceMatrixItem, evidence_matrix_item_id)
    if not matrix_item or matrix_item.case_id != case_id:
        raise ValueError(f"Item da matriz de prova {evidence_matrix_item_id} não encontrado.")
    return matrix_item


async def _matrix_validation_alert(
    db: AsyncSession,
    matrix_item: EvidenceMatrixItem,
) -> ReportSectionEvidenceMatrixAlert | None:
    if not matrix_item.evidence_ids:
        return ReportSectionEvidenceMatrixAlert(
            level="atencao",
            message="Item da matriz não possui evidência validada vinculada.",
            evidence_matrix_item_id=matrix_item.id,
        )

    validated_count = await db.scalar(
        select(func.count(EvidenceItem.id)).where(
            EvidenceItem.id.in_(matrix_item.evidence_ids),
            EvidenceItem.validation_status == "validated",
        )
    )
    if validated_count and validated_count > 0:
        return None
    return ReportSectionEvidenceMatrixAlert(
        level="atencao",
        message="Item da matriz não possui evidência validada vinculada.",
        evidence_matrix_item_id=matrix_item.id,
    )


def _to_link_response(
    link: ReportSectionEvidenceMatrixLink,
    alert: ReportSectionEvidenceMatrixAlert | None,
) -> ReportSectionEvidenceMatrixLinkResponse:
    return ReportSectionEvidenceMatrixLinkResponse(
        id=link.id,
        report_section_id=link.report_section_id,
        evidence_matrix_item_id=link.evidence_matrix_item_id,
        linked_by_id=link.linked_by_id,
        created_at=link.created_at,
        alert=alert,
    )
