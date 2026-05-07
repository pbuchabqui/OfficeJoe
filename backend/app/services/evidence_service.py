"""Service for evidence management."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import persist_audit
from app.db.models.case import Case
from app.db.models.document import Document
from app.db.models.evidence_item import EvidenceItem
from app.db.models.page import Page
from app.schemas.evidence import EvidenceCreateRequest


async def create_evidence(
    db: AsyncSession,
    case_id: str,
    payload: EvidenceCreateRequest,
) -> EvidenceItem:
    """Create a new evidence item.

    Validates:
    - Case exists
    - Document exists and belongs to case
    - Page exists in document
    """
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    doc = await db.get(Document, payload.document_id)
    if not doc or doc.case_id != case_id:
        raise ValueError(f"Document {payload.document_id} not found in case {case_id}")

    page = await db.scalar(
        select(Page).where(
            (Page.document_id == payload.document_id) & (Page.page_number == payload.page_number)
        )
    )
    if not page:
        raise ValueError(
            f"Page {payload.page_number} not found in document {payload.document_id}"
        )

    evidence = EvidenceItem(
        case_id=case_id,
        document_id=payload.document_id,
        page_number=payload.page_number,
        text_excerpt=payload.text_excerpt,
        coordinates=payload.coordinates.model_dump() if payload.coordinates else None,
        evidence_type=payload.evidence_type.value,
        notes=payload.notes,
        reliability_level=payload.reliability_level.value,
        validated=False,
    )

    db.add(evidence)
    await db.flush()
    return evidence


async def list_evidence_by_case(
    db: AsyncSession,
    case_id: str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[EvidenceItem], int]:
    """List all evidence items for a case (paginated)."""
    from sqlalchemy import func
    total = await db.scalar(
        select(func.count(EvidenceItem.id)).where(EvidenceItem.case_id == case_id)
    )

    items = await db.scalars(
        select(EvidenceItem)
        .where(EvidenceItem.case_id == case_id)
        .order_by(EvidenceItem.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return items.all(), total or 0


async def validate_evidence(
    db: AsyncSession,
    evidence_id: str,
    user_id: str,
) -> EvidenceItem:
    """Validate an evidence item."""
    evidence = await db.get(EvidenceItem, evidence_id)
    if not evidence:
        raise ValueError(f"Evidence {evidence_id} not found")

    evidence.validation_status = "validated"
    evidence.validated = True
    evidence.validated_by = user_id
    evidence.validated_at = datetime.now(timezone.utc)
    evidence.rejection_reason = None

    await db.flush()
    return evidence


async def reject_evidence(
    db: AsyncSession,
    evidence_id: str,
    user_id: str,
    rejection_reason: str,
) -> EvidenceItem:
    """Reject an evidence item."""
    evidence = await db.get(EvidenceItem, evidence_id)
    if not evidence:
        raise ValueError(f"Evidence {evidence_id} not found")

    evidence.validation_status = "rejected"
    evidence.validated = False
    evidence.validated_by = user_id
    evidence.validated_at = datetime.now(timezone.utc)
    evidence.rejection_reason = rejection_reason

    await db.flush()
    return evidence
