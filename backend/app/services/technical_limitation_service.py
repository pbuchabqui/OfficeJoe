"""Service for technical limitations management."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.technical_limitation import TechnicalLimitation
from app.schemas.technical_limitation import (
    TechnicalLimitationCreateRequest,
    TechnicalLimitationUpdateRequest,
)


async def create_technical_limitation(
    db: AsyncSession,
    case_id: str,
    payload: TechnicalLimitationCreateRequest,
) -> TechnicalLimitation:
    """Create a new technical limitation.

    Validates:
    - Case exists
    - Diligence and quesito (if provided) exist and belong to case
    """
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    if payload.diligence_id:
        from app.db.models.diligence import Diligence

        diligence = await db.get(Diligence, payload.diligence_id)
        if not diligence:
            raise ValueError(f"Diligence {payload.diligence_id} not found")
        if diligence.case_id != case_id:
            raise ValueError(
                f"Diligence {payload.diligence_id} does not belong to case {case_id}"
            )

    if payload.quesito_id:
        from app.db.models.quesito import Quesito

        quesito = await db.get(Quesito, payload.quesito_id)
        if not quesito:
            raise ValueError(f"Quesito {payload.quesito_id} not found")
        if quesito.case_id != case_id:
            raise ValueError(
                f"Quesito {payload.quesito_id} does not belong to case {case_id}"
            )

    limitation = TechnicalLimitation(
        case_id=case_id,
        type=payload.type,
        description=payload.description,
        technical_impact=payload.technical_impact,
        criticality=payload.criticality,
        status="draft",
        diligence_id=payload.diligence_id,
        quesito_id=payload.quesito_id,
    )

    db.add(limitation)
    await db.flush()
    return limitation


async def read_technical_limitation(
    db: AsyncSession,
    limitation_id: str,
) -> TechnicalLimitation:
    """Get a specific technical limitation."""
    limitation = await db.get(TechnicalLimitation, limitation_id)
    if not limitation:
        raise ValueError(f"Technical limitation {limitation_id} not found")
    return limitation


async def update_technical_limitation(
    db: AsyncSession,
    limitation_id: str,
    case_id: str,
    payload: TechnicalLimitationUpdateRequest,
) -> TechnicalLimitation:
    """Update a technical limitation.

    Validates:
    - Limitation exists and belongs to case
    - Related records (if updated) belong to case
    """
    limitation = await db.get(TechnicalLimitation, limitation_id)
    if not limitation:
        raise ValueError(f"Technical limitation {limitation_id} not found")

    if limitation.case_id != case_id:
        raise ValueError(
            f"Technical limitation {limitation_id} does not belong to case {case_id}"
        )

    if payload.diligence_id is not None:
        from app.db.models.diligence import Diligence

        if payload.diligence_id:
            diligence = await db.get(Diligence, payload.diligence_id)
            if not diligence:
                raise ValueError(f"Diligence {payload.diligence_id} not found")
            if diligence.case_id != case_id:
                raise ValueError(
                    f"Diligence {payload.diligence_id} does not belong to case {case_id}"
                )
        limitation.diligence_id = payload.diligence_id

    if payload.quesito_id is not None:
        from app.db.models.quesito import Quesito

        if payload.quesito_id:
            quesito = await db.get(Quesito, payload.quesito_id)
            if not quesito:
                raise ValueError(f"Quesito {payload.quesito_id} not found")
            if quesito.case_id != case_id:
                raise ValueError(
                    f"Quesito {payload.quesito_id} does not belong to case {case_id}"
                )
        limitation.quesito_id = payload.quesito_id

    if payload.type is not None:
        limitation.type = payload.type
    if payload.description is not None:
        limitation.description = payload.description
    if payload.technical_impact is not None:
        limitation.technical_impact = payload.technical_impact
    if payload.criticality is not None:
        limitation.criticality = payload.criticality
    if payload.status is not None:
        limitation.status = payload.status

    await db.flush()
    return limitation


async def delete_technical_limitation(
    db: AsyncSession,
    limitation_id: str,
) -> None:
    """Delete a technical limitation."""
    limitation = await db.get(TechnicalLimitation, limitation_id)
    if not limitation:
        raise ValueError(f"Technical limitation {limitation_id} not found")

    await db.delete(limitation)
    await db.flush()


async def list_technical_limitations_by_case(
    db: AsyncSession,
    case_id: str,
    criticality: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TechnicalLimitation], int]:
    """List technical limitations for a case with optional criticality filter."""
    query = select(TechnicalLimitation).where(TechnicalLimitation.case_id == case_id)

    if criticality:
        query = query.where(TechnicalLimitation.criticality == criticality)

    total = await db.scalar(
        select(func.count(TechnicalLimitation.id)).where(
            TechnicalLimitation.case_id == case_id
        )
        if not criticality
        else select(func.count(TechnicalLimitation.id)).where(
            (TechnicalLimitation.case_id == case_id)
            & (TechnicalLimitation.criticality == criticality)
        )
    )

    limitations = await db.scalars(
        query.order_by(TechnicalLimitation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return limitations.all(), total or 0
