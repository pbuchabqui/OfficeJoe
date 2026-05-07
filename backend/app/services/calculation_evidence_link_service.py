"""Service for linking calculation versions to evidence items."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.calculation import Calculation, CalculationVersion
from app.db.models.calculation_evidence_link import CalculationEvidenceLink
from app.db.models.evidence_item import EvidenceItem
from app.schemas.calculation_evidence_link import (
    CalculationEvidenceAlert,
    CalculationEvidenceLinkResponse,
    CalculationEvidenceUnlinkResponse,
)


async def link_evidence_to_calculation_version(
    db: AsyncSession,
    case_id: str,
    calculation_version_id: str,
    evidence_item_id: str,
    linked_by_id: str | None,
) -> CalculationEvidenceLinkResponse:
    version = await _get_version_for_case(db, case_id, calculation_version_id)
    evidence = await _get_evidence_for_case(db, case_id, evidence_item_id)

    existing = await db.scalar(
        select(CalculationEvidenceLink).where(
            CalculationEvidenceLink.calculation_version_id == version.id,
            CalculationEvidenceLink.evidence_item_id == evidence.id,
        )
    )
    if existing:
        link = existing
    else:
        link = CalculationEvidenceLink(
            id=str(uuid.uuid4()),
            calculation_version_id=version.id,
            evidence_item_id=evidence.id,
            linked_by_id=linked_by_id,
        )
        db.add(link)
        await db.flush()

    return _to_link_response(link, evidence)


async def unlink_evidence_from_calculation_version(
    db: AsyncSession,
    case_id: str,
    calculation_version_id: str,
    evidence_item_id: str,
) -> CalculationEvidenceUnlinkResponse:
    await _get_version_for_case(db, case_id, calculation_version_id)
    await _get_evidence_for_case(db, case_id, evidence_item_id)

    result = await db.execute(
        delete(CalculationEvidenceLink).where(
            CalculationEvidenceLink.calculation_version_id == calculation_version_id,
            CalculationEvidenceLink.evidence_item_id == evidence_item_id,
        )
    )
    return CalculationEvidenceUnlinkResponse(
        calculation_version_id=calculation_version_id,
        evidence_item_id=evidence_item_id,
        removed=(result.rowcount or 0) > 0,
    )


async def _get_version_for_case(
    db: AsyncSession,
    case_id: str,
    calculation_version_id: str,
) -> CalculationVersion:
    result = await db.execute(
        select(CalculationVersion)
        .join(Calculation, Calculation.id == CalculationVersion.calculation_id)
        .where(
            CalculationVersion.id == calculation_version_id,
            Calculation.case_id == case_id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise ValueError(f"Versão de cálculo {calculation_version_id} não encontrada.")
    return version


async def _get_evidence_for_case(
    db: AsyncSession,
    case_id: str,
    evidence_item_id: str,
) -> EvidenceItem:
    evidence = await db.get(EvidenceItem, evidence_item_id)
    if not evidence or evidence.case_id != case_id:
        raise ValueError(f"Evidência {evidence_item_id} não encontrada.")
    return evidence


def _to_link_response(
    link: CalculationEvidenceLink,
    evidence: EvidenceItem,
) -> CalculationEvidenceLinkResponse:
    return CalculationEvidenceLinkResponse(
        id=link.id,
        calculation_version_id=link.calculation_version_id,
        evidence_item_id=link.evidence_item_id,
        linked_by_id=link.linked_by_id,
        created_at=link.created_at,
        alert=_validation_alert(evidence),
    )


def _validation_alert(evidence: EvidenceItem) -> CalculationEvidenceAlert | None:
    if evidence.validated and evidence.validation_status == "validated":
        return None
    return CalculationEvidenceAlert(
        level="atencao",
        message="Evidência vinculada ainda não está validada.",
        evidence_item_id=evidence.id,
    )
