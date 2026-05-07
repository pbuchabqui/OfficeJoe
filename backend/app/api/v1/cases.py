"""
Endpoints CRUD de processos periciais.

GET    /api/v1/cases               – lista paginada com filtros opcionais
POST   /api/v1/cases               – criar processo
GET    /api/v1/cases/{id}          – detalhe
PATCH  /api/v1/cases/{id}          – atualização parcial
DELETE /api/v1/cases/{id}          – soft delete
"""
from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, persist_audit, require_permission
from app.core.audit import AuditAction, log_audit
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.case import CaseCreate, CaseDetail, CaseSummary, CaseUpdate, PaginatedCases
from app.services.case_service import (
    create_case,
    get_case,
    list_cases,
    soft_delete_case,
    update_case,
)

router = APIRouter(prefix="/cases", tags=["Processos Periciais"])


@router.get("", response_model=PaginatedCases)
async def list_cases_endpoint(
    status: Optional[str] = Query(None, description="Filtrar por status interno"),
    case_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(20, ge=1, le=100, description="Itens por página"),
    current_user: User = Depends(require_permission("case:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCases:
    items, total = await list_cases(db, status=status, case_type=case_type, page=page, size=size)
    pages = max(1, math.ceil(total / size))
    return PaginatedCases(
        items=[CaseSummary.model_validate(c) for c in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
async def create_case_endpoint(
    payload: CaseCreate,
    request: Request,
    current_user: User = Depends(require_permission("case:write")),
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    try:
        case = await create_case(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    entry = log_audit(
        action=AuditAction.CASE_CREATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="case",
        resource_id=case.id,
        details={"case_number": case.case_number, "case_type": case.case_type},
    )
    await persist_audit(entry, db, case_id=case.id)

    return CaseDetail.model_validate(case)


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case_endpoint(
    case_id: str,
    current_user: User = Depends(require_permission("case:read")),
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    case = await get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")
    return CaseDetail.model_validate(case)


@router.patch("/{case_id}", response_model=CaseDetail)
async def update_case_endpoint(
    case_id: str,
    payload: CaseUpdate,
    request: Request,
    current_user: User = Depends(require_permission("case:write")),
    db: AsyncSession = Depends(get_db),
) -> CaseDetail:
    case = await get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")

    old_status = case.status
    updated = await update_case(db, case, payload)

    update_data = payload.model_dump(exclude_none=True)
    action = (
        AuditAction.CASE_STATUS_CHANGED
        if "status" in update_data
        else AuditAction.CASE_UPDATED
    )
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

    return CaseDetail.model_validate(updated)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_endpoint(
    case_id: str,
    request: Request,
    current_user: User = Depends(require_permission("case:delete")),
    db: AsyncSession = Depends(get_db),
):
    case = await get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")

    await soft_delete_case(db, case)

    entry = log_audit(
        action=AuditAction.CASE_UPDATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="case",
        resource_id=case_id,
        details={"action": "soft_delete", "case_number": case.case_number},
    )
    await persist_audit(entry, db)
