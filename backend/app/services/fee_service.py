"""Service for initial expert fee CRUD."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.fee import Fee
from app.schemas.fee import FeeCreateRequest, FeeUpdateRequest


async def create_fee(
    db: AsyncSession,
    case_id: str,
    payload: FeeCreateRequest,
) -> Fee:
    await _validate_case_exists(db, case_id)
    fee = Fee(
        case_id=case_id,
        proposed_amount=payload.proposed_amount,
        arbitrated_amount=payload.arbitrated_amount,
        deposited_amount=payload.deposited_amount,
        withdrawn_amount=payload.withdrawn_amount,
        status=payload.status,
        proposed_at=payload.proposed_at,
        arbitrated_at=payload.arbitrated_at,
        deposited_at=payload.deposited_at,
        withdrawn_at=payload.withdrawn_at,
        notes=payload.notes,
    )
    db.add(fee)
    await db.flush()
    return fee


async def read_fee(db: AsyncSession, fee_id: str) -> Fee:
    fee = await db.get(Fee, fee_id)
    if not fee:
        raise ValueError(f"Fee {fee_id} not found")
    return fee


async def update_fee(
    db: AsyncSession,
    fee_id: str,
    case_id: str,
    payload: FeeUpdateRequest,
) -> Fee:
    fee = await read_fee(db, fee_id)
    if fee.case_id != case_id:
        raise ValueError(f"Fee {fee_id} does not belong to case {case_id}")

    if payload.proposed_amount is not None:
        fee.proposed_amount = payload.proposed_amount
    if payload.arbitrated_amount is not None:
        fee.arbitrated_amount = payload.arbitrated_amount
    if payload.deposited_amount is not None:
        fee.deposited_amount = payload.deposited_amount
    if payload.withdrawn_amount is not None:
        fee.withdrawn_amount = payload.withdrawn_amount
    if payload.status is not None:
        fee.status = payload.status
    if payload.proposed_at is not None:
        fee.proposed_at = payload.proposed_at
    if payload.arbitrated_at is not None:
        fee.arbitrated_at = payload.arbitrated_at
    if payload.deposited_at is not None:
        fee.deposited_at = payload.deposited_at
    if payload.withdrawn_at is not None:
        fee.withdrawn_at = payload.withdrawn_at
    if payload.notes is not None:
        fee.notes = payload.notes

    await db.flush()
    return fee


async def delete_fee(db: AsyncSession, fee_id: str) -> None:
    fee = await read_fee(db, fee_id)
    await db.delete(fee)
    await db.flush()


async def list_fees_by_case(
    db: AsyncSession,
    case_id: str,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Fee], int]:
    await _validate_case_exists(db, case_id)
    filters = [Fee.case_id == case_id]
    if status:
        filters.append(Fee.status == status)

    total = await db.scalar(select(func.count(Fee.id)).where(*filters))
    result = await db.execute(
        select(Fee)
        .where(*filters)
        .order_by(Fee.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all(), total or 0


async def _validate_case_exists(db: AsyncSession, case_id: str) -> Case:
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")
    return case
