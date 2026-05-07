"""
Endpoints CRUD de processos periciais (Cases).
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_client_ip, get_current_user, persist_audit, require_permission
from app.core.audit import AuditAction, log_audit
from app.db.models.case import Case, CaseParty
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.case import CaseCreate, CaseDetail, CaseSummary, CaseUpdate

router = APIRouter(prefix="/cases", tags=["Processos Periciais"])


@router.get("", response_model=List[CaseSummary])
async def list_cases(
    status: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    current_user: User = Depends(require_permission("case:read")),
    db: AsyncSession = Depends(get_db),
) -> List[CaseSummary]:
    q = select(Case)
    if status:
        q = q.where(Case.status == status)
    if case_type:
        q = q.where(Case.case_type == case_type)
    q = q.order_by(Case.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    cases = result.scalars().all()
    return [CaseSummary.model_validate(c) for c in cases]


@router.post("", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate,
    request: Request,
    current_user: User = Depends(require_permission("case:write")),
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    existing = await db.execute(select(Case).where(Case.case_number == payload.case_number))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Processo {payload.case_number} já cadastrado.",
        )

    case_id = str(uuid.uuid4())
    case = Case(
        id=case_id,
        case_number=payload.case_number,
        case_type=payload.case_type,
        title=payload.title,
        description=payload.description,
        court=payload.court,
        court_district=payload.court_district,
        judge_name=payload.judge_name,
        appointment_date=payload.appointment_date,
        deadline_date=payload.deadline_date,
        filing_date=payload.filing_date,
        honorarium_proposed=payload.honorarium_proposed,
        responsible_user_id=current_user.id,
    )
    db.add(case)

    for p in payload.parties:
        party = CaseParty(
            id=str(uuid.uuid4()),
            case_id=case_id,
            name=p.name,
            role=p.role,
            cpf_cnpj=p.cpf_cnpj,
            lawyer_name=p.lawyer_name,
            lawyer_oab=p.lawyer_oab,
        )
        db.add(party)

    await db.flush()

    entry = log_audit(
        action=AuditAction.CASE_CREATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="case",
        resource_id=case_id,
        details={"case_number": payload.case_number, "case_type": payload.case_type},
    )
    await persist_audit(entry, db, case_id=case_id)

    # Recarrega com relacionamentos
    result = await db.execute(
        select(Case).where(Case.id == case_id).options(selectinload(Case.parties))
    )
    return CaseDetail.model_validate(result.scalar_one())


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(
    case_id: str,
    current_user: User = Depends(require_permission("case:read")),
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    result = await db.execute(
        select(Case).where(Case.id == case_id).options(selectinload(Case.parties))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")
    return CaseDetail.model_validate(case)


@router.patch("/{case_id}", response_model=CaseDetail)
async def update_case(
    case_id: str,
    payload: CaseUpdate,
    request: Request,
    current_user: User = Depends(require_permission("case:write")),
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    result = await db.execute(
        select(Case).where(Case.id == case_id).options(selectinload(Case.parties))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")

    old_status = case.status
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    await db.flush()

    action = AuditAction.CASE_STATUS_CHANGED if "status" in update_data else AuditAction.CASE_UPDATED
    entry = log_audit(
        action=action,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="case",
        resource_id=case_id,
        details={**update_data, "old_status": old_status},
    )
    await persist_audit(entry, db, case_id=case_id)

    result = await db.execute(
        select(Case).where(Case.id == case_id).options(selectinload(Case.parties))
    )
    return CaseDetail.model_validate(result.scalar_one())


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    request: Request,
    current_user: User = Depends(require_permission("case:delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")

    await db.delete(case)

    entry = log_audit(
        action=AuditAction.CASE_UPDATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="case",
        resource_id=case_id,
        details={"action": "delete", "case_number": case.case_number},
    )
    await persist_audit(entry, db)
