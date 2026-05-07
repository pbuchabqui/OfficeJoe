"""
Serviço de processos periciais.

Concentra a lógica de negócio de CRUD de cases, mantendo os endpoints finos.
Todos os métodos recebem uma AsyncSession já aberta (sem commit — a sessão
é gerenciada pelo get_db dependency que faz commit ao encerrar a requisição).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.case import Case, CaseParty, CaseStatus
from app.schemas.case import CaseCreate, CaseUpdate


async def get_case(db: AsyncSession, case_id: str) -> Optional[Case]:
    """Retorna case ativo pelo id, ou None se não existir / estiver deletado."""
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id, Case.deleted_at.is_(None))
        .options(selectinload(Case.parties))
    )
    return result.scalar_one_or_none()


async def get_case_by_number(db: AsyncSession, case_number: str) -> Optional[Case]:
    result = await db.execute(
        select(Case).where(Case.case_number == case_number, Case.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def list_cases(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    case_type: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> Tuple[list[Case], int]:
    """
    Retorna (lista de cases, total) com paginação e filtros opcionais.
    Exclui automaticamente registros com deleted_at preenchido.
    """
    base_q = select(Case).where(Case.deleted_at.is_(None))
    if status:
        base_q = base_q.where(Case.status == status)
    if case_type:
        base_q = base_q.where(Case.case_type == case_type)

    count_q = select(func.count()).select_from(base_q.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * size
    items_q = base_q.order_by(Case.created_at.desc()).offset(offset).limit(size)
    rows = await db.execute(items_q)
    items = list(rows.scalars().all())

    return items, total


async def create_case(
    db: AsyncSession,
    payload: CaseCreate,
    responsible_user_id: str,
) -> Case:
    """Cria case e suas partes. Lança ValueError se o número CNJ já existir."""
    existing = await get_case_by_number(db, payload.case_number)
    if existing:
        raise ValueError(f"Processo {payload.case_number} já cadastrado.")

    case_id = str(uuid.uuid4())
    case = Case(
        id=case_id,
        case_number=payload.case_number,
        case_type=payload.case_type,
        status=CaseStatus.PLANEJAMENTO.value,
        title=payload.title,
        tribunal=payload.tribunal,
        vara=payload.vara,
        court_district=payload.court_district,
        fase_processual=payload.fase_processual,
        objeto_pericia=payload.objeto_pericia,
        appointment_date=payload.appointment_date,
        data_ciencia=payload.data_ciencia,
        deadline_date=payload.deadline_date,
        notes=payload.notes,
        honorarium_proposed_cents=payload.honorarium_proposed_cents,
        responsible_user_id=responsible_user_id,
    )
    db.add(case)

    for p in payload.parties:
        db.add(CaseParty(
            id=str(uuid.uuid4()),
            case_id=case_id,
            name=p.name,
            role=p.role,
            cpf_cnpj=p.cpf_cnpj,
            lawyer_name=p.lawyer_name,
            lawyer_oab=p.lawyer_oab,
        ))

    await db.flush()

    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.parties))
    )
    return result.scalar_one()


async def update_case(
    db: AsyncSession,
    case: Case,
    payload: CaseUpdate,
) -> Case:
    """Aplica patch parcial no case. Ignora campos None."""
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    await db.flush()

    result = await db.execute(
        select(Case)
        .where(Case.id == case.id)
        .options(selectinload(Case.parties))
    )
    return result.scalar_one()


async def soft_delete_case(db: AsyncSession, case: Case) -> None:
    """Soft delete: preenche deleted_at. Não remove o registro."""
    case.deleted_at = datetime.now(timezone.utc).isoformat()
    await db.flush()
