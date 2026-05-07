"""Service for evidence matrix management."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.evidence_item import EvidenceItem
from app.db.models.evidence_matrix_item import EvidenceMatrixItem
from app.schemas.evidence_matrix import EvidenceMatrixCreateRequest, EvidenceMatrixUpdateRequest


async def create_evidence_matrix(
    db: AsyncSession,
    case_id: str,
    payload: EvidenceMatrixCreateRequest,
) -> EvidenceMatrixItem:
    """Create a new evidence matrix item.

    Validates:
    - Case exists
    - All evidence IDs exist and belong to the case
    - At least one evidence is linked
    """
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    if len(payload.evidence_ids) == 0:
        raise ValueError("Deve estar vinculada pelo menos uma evidência")

    evidence_count = await db.scalar(
        select(func.count(EvidenceItem.id)).where(
            (EvidenceItem.case_id == case_id) & (EvidenceItem.id.in_(payload.evidence_ids))
        )
    )

    if evidence_count != len(payload.evidence_ids):
        raise ValueError(
            f"Uma ou mais evidências não existem ou não pertencem ao caso {case_id}"
        )

    matrix_item = EvidenceMatrixItem(
        case_id=case_id,
        disputed_fact=payload.disputed_fact,
        theme=payload.theme,
        evidence_ids=payload.evidence_ids,
        expert_procedure=payload.expert_procedure,
        methodology_or_criteria=payload.methodology_or_criteria,
        result_found=payload.result_found,
        technical_impact=payload.technical_impact,
        status="draft",
    )

    db.add(matrix_item)
    await db.flush()
    return matrix_item


async def read_evidence_matrix(
    db: AsyncSession,
    matrix_id: str,
) -> EvidenceMatrixItem:
    """Get a specific matrix item."""
    matrix_item = await db.get(EvidenceMatrixItem, matrix_id)
    if not matrix_item:
        raise ValueError(f"Matrix item {matrix_id} not found")
    return matrix_item


async def update_evidence_matrix(
    db: AsyncSession,
    matrix_id: str,
    case_id: str,
    payload: EvidenceMatrixUpdateRequest,
) -> EvidenceMatrixItem:
    """Update a matrix item.

    Validates evidence if evidence_ids are being updated.
    """
    matrix_item = await db.get(EvidenceMatrixItem, matrix_id)
    if not matrix_item:
        raise ValueError(f"Matrix item {matrix_id} not found")

    if matrix_item.case_id != case_id:
        raise ValueError(f"Matrix item {matrix_id} does not belong to case {case_id}")

    if payload.evidence_ids is not None:
        if len(payload.evidence_ids) == 0:
            raise ValueError("Deve estar vinculada pelo menos uma evidência")

        evidence_count = await db.scalar(
            select(func.count(EvidenceItem.id)).where(
                (EvidenceItem.case_id == case_id) & (EvidenceItem.id.in_(payload.evidence_ids))
            )
        )

        if evidence_count != len(payload.evidence_ids):
            raise ValueError(
                f"Uma ou mais evidências não existem ou não pertencem ao caso {case_id}"
            )

        matrix_item.evidence_ids = payload.evidence_ids

    if payload.disputed_fact is not None:
        matrix_item.disputed_fact = payload.disputed_fact
    if payload.theme is not None:
        matrix_item.theme = payload.theme
    if payload.expert_procedure is not None:
        matrix_item.expert_procedure = payload.expert_procedure
    if payload.methodology_or_criteria is not None:
        matrix_item.methodology_or_criteria = payload.methodology_or_criteria
    if payload.result_found is not None:
        matrix_item.result_found = payload.result_found
    if payload.technical_impact is not None:
        matrix_item.technical_impact = payload.technical_impact
    if payload.status is not None:
        matrix_item.status = payload.status

    await db.flush()
    return matrix_item


async def delete_evidence_matrix(
    db: AsyncSession,
    matrix_id: str,
) -> None:
    """Delete a matrix item."""
    matrix_item = await db.get(EvidenceMatrixItem, matrix_id)
    if not matrix_item:
        raise ValueError(f"Matrix item {matrix_id} not found")

    await db.delete(matrix_item)
    await db.flush()


async def list_evidence_matrix_by_case(
    db: AsyncSession,
    case_id: str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[EvidenceMatrixItem], int]:
    """List all matrix items for a case (paginated)."""
    total = await db.scalar(
        select(func.count(EvidenceMatrixItem.id)).where(EvidenceMatrixItem.case_id == case_id)
    )

    items = await db.scalars(
        select(EvidenceMatrixItem)
        .where(EvidenceMatrixItem.case_id == case_id)
        .order_by(EvidenceMatrixItem.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return items.all(), total or 0
