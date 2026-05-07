"""Tests for diligence management."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case, CaseStatus, CaseType
from app.db.models.diligence import Diligence
from app.db.models.diligence_item import DiligenceItem
from app.schemas.diligence import (
    DiligenceCreateRequest,
    DiligenceItemCreateRequest,
    DiligenceItemUpdateRequest,
    DiligenceUpdateRequest,
)
from app.services.diligence_service import (
    create_diligence,
    read_diligence,
    update_diligence,
    delete_diligence,
    list_diligences_by_case,
    add_item,
    update_item,
    delete_item,
    list_items_by_diligence,
)


async def _make_case(db: AsyncSession, user_id: str) -> Case:
    """Helper to create a test case."""
    case = Case(
        id=str(uuid.uuid4()),
        case_number=f"000{uuid.uuid4().hex[:4]}-56.2024.5.02.0000",
        case_type=CaseType.TRABALHISTA.value,
        title="Test Case",
        status=CaseStatus.PLANEJAMENTO.value,
        responsible_user_id=user_id,
    )
    db.add(case)
    await db.flush()
    return case


# ── Service Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_diligence_success(db_session: AsyncSession):
    """Criar diligência com dados válidos."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user1@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-001",
        recipient="Cliente",
        deadline=deadline,
        observations="Solicitação inicial",
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Necessário para análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    assert diligence.case_id == case.id
    assert diligence.number == "2024-001"
    assert diligence.recipient == "Cliente"
    assert diligence.status == "draft"

    items = await list_items_by_diligence(db_session, diligence.id)
    assert len(items) == 1
    assert items[0].requested_document == "Contrato"
    assert items[0].status == "pending"


@pytest.mark.asyncio
async def test_create_diligence_multiple_items(db_session: AsyncSession):
    """Criar diligência com múltiplos itens."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user2@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-002",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise de cláusulas",
            ),
            DiligenceItemCreateRequest(
                requested_document="Recibos",
                period="2024-01 a 2024-03",
                technical_justification="Comprovação de pagamentos",
            ),
            DiligenceItemCreateRequest(
                requested_document="Comunicações",
                period="2024-01 a 2024-03",
                technical_justification="Evidência de acordos",
            ),
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    items = await list_items_by_diligence(db_session, diligence.id)
    assert len(items) == 3
    assert items[0].requested_document == "Contrato"
    assert items[1].requested_document == "Recibos"
    assert items[2].requested_document == "Comunicações"


@pytest.mark.asyncio
async def test_create_diligence_case_not_found(db_session: AsyncSession):
    """Erro se processo não existe."""
    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-003",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    with pytest.raises(ValueError, match="Case .* not found"):
        await create_diligence(db_session, "invalid-case", payload)


@pytest.mark.asyncio
async def test_create_diligence_no_items(db_session: AsyncSession):
    """Erro se nenhum item fornecido."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user3@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    from pydantic import ValidationError

    deadline = datetime.utcnow() + timedelta(days=30)

    with pytest.raises(ValidationError, match="List should have at least 1 item"):
        DiligenceCreateRequest(
            number="2024-004",
            recipient="Cliente",
            deadline=deadline,
            items=[],
        )


@pytest.mark.asyncio
async def test_read_diligence(db_session: AsyncSession):
    """Obter diligência existente."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user4@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-005",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    read_diligence_obj = await read_diligence(db_session, diligence.id)

    assert read_diligence_obj.id == diligence.id
    assert read_diligence_obj.number == "2024-005"


@pytest.mark.asyncio
async def test_read_diligence_not_found(db_session: AsyncSession):
    """Erro ao obter diligência inexistente."""
    with pytest.raises(ValueError, match="Diligence .* not found"):
        await read_diligence(db_session, "invalid-id")


@pytest.mark.asyncio
async def test_update_diligence(db_session: AsyncSession):
    """Atualizar diligência."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user5@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-006",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)

    update_payload = DiligenceUpdateRequest(
        recipient="Novo Destinatário",
        status="pending",
    )

    updated = await update_diligence(db_session, diligence.id, case.id, update_payload)

    assert updated.recipient == "Novo Destinatário"
    assert updated.status == "pending"
    assert updated.number == "2024-006"


@pytest.mark.asyncio
async def test_update_diligence_not_found(db_session: AsyncSession):
    """Erro ao atualizar diligência inexistente."""
    payload = DiligenceUpdateRequest(recipient="Novo Destinatário")

    with pytest.raises(ValueError, match="Diligence .* not found"):
        await update_diligence(db_session, "invalid-id", "case-id", payload)


@pytest.mark.asyncio
async def test_delete_diligence(db_session: AsyncSession):
    """Deletar diligência (cascata para itens)."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user6@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-007",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    diligence_id = diligence.id

    await delete_diligence(db_session, diligence_id)

    with pytest.raises(ValueError, match="Diligence .* not found"):
        await read_diligence(db_session, diligence_id)


@pytest.mark.asyncio
async def test_list_diligences_by_case(db_session: AsyncSession):
    """Listar diligências de um processo."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user7@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)

    for i in range(3):
        payload = DiligenceCreateRequest(
            number=f"2024-{100+i}",
            recipient="Cliente",
            deadline=deadline,
            items=[
                DiligenceItemCreateRequest(
                    requested_document="Contrato",
                    period="2024-01 a 2024-03",
                    technical_justification="Análise",
                )
            ],
        )
        await create_diligence(db_session, case.id, payload)

    diligences, total = await list_diligences_by_case(db_session, case.id)

    assert total == 3
    assert len(diligences) == 3


@pytest.mark.asyncio
async def test_list_diligences_pagination(db_session: AsyncSession):
    """Listar diligências com paginação."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user8@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)

    for i in range(5):
        payload = DiligenceCreateRequest(
            number=f"2024-{200+i}",
            recipient="Cliente",
            deadline=deadline,
            items=[
                DiligenceItemCreateRequest(
                    requested_document="Contrato",
                    period="2024-01 a 2024-03",
                    technical_justification="Análise",
                )
            ],
        )
        await create_diligence(db_session, case.id, payload)

    page1, total1 = await list_diligences_by_case(db_session, case.id, limit=2, offset=0)
    page2, total2 = await list_diligences_by_case(db_session, case.id, limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert total1 == 5
    assert total2 == 5


@pytest.mark.asyncio
async def test_add_item_to_diligence(db_session: AsyncSession):
    """Adicionar item a uma diligência."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user9@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-301",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    items_before = await list_items_by_diligence(db_session, diligence.id)
    assert len(items_before) == 1

    item_payload = DiligenceItemCreateRequest(
        requested_document="Recibos",
        period="2024-01 a 2024-03",
        technical_justification="Comprovação",
    )

    new_item = await add_item(db_session, diligence.id, item_payload)
    await db_session.commit()

    assert new_item.diligence_id == diligence.id
    assert new_item.requested_document == "Recibos"
    assert new_item.status == "pending"


@pytest.mark.asyncio
async def test_update_item(db_session: AsyncSession):
    """Atualizar item de diligência."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user10@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-302",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    items = await list_items_by_diligence(db_session, diligence.id)
    item = items[0]

    item_update = DiligenceItemUpdateRequest(status="provided")

    updated = await update_item(db_session, item.id, diligence.id, item_update)
    await db_session.commit()

    assert updated.status == "provided"
    assert updated.requested_document == "Contrato"


@pytest.mark.asyncio
async def test_delete_item(db_session: AsyncSession):
    """Deletar item de diligência."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user11@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-303",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            ),
            DiligenceItemCreateRequest(
                requested_document="Recibos",
                period="2024-01 a 2024-03",
                technical_justification="Comprovação",
            ),
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    items = await list_items_by_diligence(db_session, diligence.id)
    item_to_delete = items[0]

    await delete_item(db_session, item_to_delete.id)
    await db_session.commit()

    remaining_items = await list_items_by_diligence(db_session, diligence.id)
    assert len(remaining_items) == 1
    assert remaining_items[0].requested_document == "Recibos"


@pytest.mark.asyncio
async def test_list_items_by_diligence(db_session: AsyncSession):
    """Listar itens de uma diligência."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="dilig-user12@teste.com",
        full_name="Diligence User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-304",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Contrato",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            ),
            DiligenceItemCreateRequest(
                requested_document="Recibos",
                period="2024-01 a 2024-03",
                technical_justification="Comprovação",
            ),
            DiligenceItemCreateRequest(
                requested_document="Comunicações",
                period="2024-01 a 2024-03",
                technical_justification="Acordos",
            ),
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)

    items = await list_items_by_diligence(db_session, diligence.id)

    assert len(items) == 3
    assert items[0].requested_document == "Contrato"
    assert items[1].requested_document == "Recibos"
    assert items[2].requested_document == "Comunicações"
