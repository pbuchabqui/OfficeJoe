"""Service for diligence management."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.diligence import Diligence
from app.db.models.diligence_item import DiligenceItem
from app.schemas.diligence import (
    DiligenceCreateRequest,
    DiligenceItemCreateRequest,
    DiligenceItemUpdateRequest,
    DiligenceUpdateRequest,
)


async def create_diligence(
    db: AsyncSession,
    case_id: str,
    payload: DiligenceCreateRequest,
) -> Diligence:
    """Create a new diligence with items.

    Validates:
    - Case exists
    - At least one item is provided
    """
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    if len(payload.items) == 0:
        raise ValueError("Diligência deve ter pelo menos um item")

    diligence = Diligence(
        case_id=case_id,
        number=payload.number,
        recipient=payload.recipient,
        deadline=payload.deadline,
        observations=payload.observations,
        status="draft",
    )

    db.add(diligence)
    await db.flush()

    for item_data in payload.items:
        item = DiligenceItem(
            diligence_id=diligence.id,
            requested_document=item_data.requested_document,
            period=item_data.period,
            technical_justification=item_data.technical_justification,
            status="pending",
        )
        db.add(item)

    await db.flush()
    return diligence


async def read_diligence(
    db: AsyncSession,
    diligence_id: str,
) -> Diligence:
    """Get a specific diligence."""
    diligence = await db.get(Diligence, diligence_id)
    if not diligence:
        raise ValueError(f"Diligence {diligence_id} not found")
    return diligence


async def update_diligence(
    db: AsyncSession,
    diligence_id: str,
    case_id: str,
    payload: DiligenceUpdateRequest,
) -> Diligence:
    """Update a diligence."""
    diligence = await db.get(Diligence, diligence_id)
    if not diligence:
        raise ValueError(f"Diligence {diligence_id} not found")

    if diligence.case_id != case_id:
        raise ValueError(f"Diligence {diligence_id} does not belong to case {case_id}")

    if payload.number is not None:
        diligence.number = payload.number
    if payload.recipient is not None:
        diligence.recipient = payload.recipient
    if payload.deadline is not None:
        diligence.deadline = payload.deadline
    if payload.observations is not None:
        diligence.observations = payload.observations
    if payload.status is not None:
        diligence.status = payload.status

    await db.flush()
    return diligence


async def delete_diligence(
    db: AsyncSession,
    diligence_id: str,
) -> None:
    """Delete a diligence (cascades to items)."""
    diligence = await db.get(Diligence, diligence_id)
    if not diligence:
        raise ValueError(f"Diligence {diligence_id} not found")

    await db.delete(diligence)
    await db.flush()


async def list_diligences_by_case(
    db: AsyncSession,
    case_id: str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Diligence], int]:
    """List all diligences for a case (paginated)."""
    total = await db.scalar(
        select(func.count(Diligence.id)).where(Diligence.case_id == case_id)
    )

    diligences = await db.scalars(
        select(Diligence)
        .where(Diligence.case_id == case_id)
        .order_by(Diligence.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return diligences.all(), total or 0


async def add_item(
    db: AsyncSession,
    diligence_id: str,
    payload: DiligenceItemCreateRequest,
) -> DiligenceItem:
    """Add a new item to a diligence."""
    diligence = await db.get(Diligence, diligence_id)
    if not diligence:
        raise ValueError(f"Diligence {diligence_id} not found")

    item = DiligenceItem(
        diligence_id=diligence_id,
        requested_document=payload.requested_document,
        period=payload.period,
        technical_justification=payload.technical_justification,
        status="pending",
    )

    db.add(item)
    await db.flush()
    return item


async def update_item(
    db: AsyncSession,
    item_id: str,
    diligence_id: str,
    payload: DiligenceItemUpdateRequest,
) -> DiligenceItem:
    """Update a diligence item."""
    item = await db.get(DiligenceItem, item_id)
    if not item:
        raise ValueError(f"Item {item_id} not found")

    if item.diligence_id != diligence_id:
        raise ValueError(f"Item {item_id} does not belong to diligence {diligence_id}")

    if payload.requested_document is not None:
        item.requested_document = payload.requested_document
    if payload.period is not None:
        item.period = payload.period
    if payload.technical_justification is not None:
        item.technical_justification = payload.technical_justification
    if payload.status is not None:
        item.status = payload.status

    await db.flush()
    return item


async def delete_item(
    db: AsyncSession,
    item_id: str,
) -> None:
    """Delete a diligence item."""
    item = await db.get(DiligenceItem, item_id)
    if not item:
        raise ValueError(f"Item {item_id} not found")

    await db.delete(item)
    await db.flush()


async def list_items_by_diligence(
    db: AsyncSession,
    diligence_id: str,
) -> list[DiligenceItem]:
    """Get all items for a diligence."""
    diligence = await db.get(Diligence, diligence_id)
    if not diligence:
        raise ValueError(f"Diligence {diligence_id} not found")

    items = await db.scalars(
        select(DiligenceItem)
        .where(DiligenceItem.diligence_id == diligence_id)
        .order_by(DiligenceItem.created_at.asc())
    )

    return items.all()
