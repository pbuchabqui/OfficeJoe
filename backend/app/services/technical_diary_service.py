"""Service for technical diary CRUD."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.technical_diary_entry import TechnicalDiaryEntry
from app.db.models.user import User
from app.schemas.technical_diary import (
    TechnicalDiaryEntryCreateRequest,
    TechnicalDiaryEntryUpdateRequest,
)


async def create_technical_diary_entry(
    db: AsyncSession,
    case_id: str,
    payload: TechnicalDiaryEntryCreateRequest,
) -> TechnicalDiaryEntry:
    await _validate_case_exists(db, case_id)
    if payload.responsible_user_id:
        await _validate_user_exists(db, payload.responsible_user_id)

    entry = TechnicalDiaryEntry(
        case_id=case_id,
        entry_date=payload.entry_date,
        responsible_user_id=payload.responsible_user_id,
        decision_type=payload.decision_type,
        description=payload.description,
        technical_justification=payload.technical_justification,
        status=payload.status,
    )
    db.add(entry)
    await db.flush()
    return entry


async def read_technical_diary_entry(
    db: AsyncSession,
    entry_id: str,
) -> TechnicalDiaryEntry:
    entry = await db.get(TechnicalDiaryEntry, entry_id)
    if not entry:
        raise ValueError(f"Technical diary entry {entry_id} not found")
    return entry


async def update_technical_diary_entry(
    db: AsyncSession,
    entry_id: str,
    case_id: str,
    payload: TechnicalDiaryEntryUpdateRequest,
) -> TechnicalDiaryEntry:
    entry = await read_technical_diary_entry(db, entry_id)
    if entry.case_id != case_id:
        raise ValueError(f"Technical diary entry {entry_id} does not belong to case {case_id}")

    if payload.responsible_user_id is not None and payload.responsible_user_id:
        await _validate_user_exists(db, payload.responsible_user_id)

    if payload.entry_date is not None:
        entry.entry_date = payload.entry_date
    if payload.responsible_user_id is not None:
        entry.responsible_user_id = payload.responsible_user_id
    if payload.decision_type is not None:
        entry.decision_type = payload.decision_type
    if payload.description is not None:
        entry.description = payload.description
    if payload.technical_justification is not None:
        entry.technical_justification = payload.technical_justification
    if payload.status is not None:
        entry.status = payload.status

    await db.flush()
    return entry


async def delete_technical_diary_entry(
    db: AsyncSession,
    entry_id: str,
) -> None:
    entry = await read_technical_diary_entry(db, entry_id)
    await db.delete(entry)
    await db.flush()


async def list_technical_diary_entries_by_case(
    db: AsyncSession,
    case_id: str,
    decision_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TechnicalDiaryEntry], int]:
    await _validate_case_exists(db, case_id)

    filters = [TechnicalDiaryEntry.case_id == case_id]
    if decision_type:
        filters.append(TechnicalDiaryEntry.decision_type == decision_type)
    if status:
        filters.append(TechnicalDiaryEntry.status == status)

    total = await db.scalar(
        select(func.count(TechnicalDiaryEntry.id)).where(*filters)
    )
    result = await db.execute(
        select(TechnicalDiaryEntry)
        .where(*filters)
        .order_by(TechnicalDiaryEntry.entry_date.desc(), TechnicalDiaryEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all(), total or 0


async def _validate_case_exists(db: AsyncSession, case_id: str) -> Case:
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")
    return case


async def _validate_user_exists(db: AsyncSession, user_id: str) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    return user
