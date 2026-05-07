"""Tests for technical limitations."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case, CaseStatus, CaseType
from app.db.models.technical_limitation import TechnicalLimitation
from app.schemas.technical_limitation import (
    TechnicalLimitationCreateRequest,
    TechnicalLimitationUpdateRequest,
)
from app.services.technical_limitation_service import (
    create_technical_limitation,
    read_technical_limitation,
    update_technical_limitation,
    delete_technical_limitation,
    list_technical_limitations_by_case,
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
async def test_create_technical_limitation_success(db_session: AsyncSession):
    """Criar limitação técnica com dados válidos."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user1@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    payload = TechnicalLimitationCreateRequest(
        type="escopo",
        description="Acesso limitado aos servidores",
        technical_impact="Não foi possível analisar dados críticos",
        criticality="alta",
    )

    limitation = await create_technical_limitation(db_session, case.id, payload)

    assert limitation.case_id == case.id
    assert limitation.type == "escopo"
    assert limitation.description == "Acesso limitado aos servidores"
    assert limitation.criticality == "alta"
    assert limitation.status == "draft"


@pytest.mark.asyncio
async def test_create_technical_limitation_case_not_found(db_session: AsyncSession):
    """Erro se processo não existe."""
    payload = TechnicalLimitationCreateRequest(
        type="escopo",
        description="Descrição",
        technical_impact="Impacto",
        criticality="média",
    )

    with pytest.raises(ValueError, match="Case .* not found"):
        await create_technical_limitation(db_session, "invalid-case", payload)


@pytest.mark.asyncio
async def test_create_technical_limitation_with_diligence(db_session: AsyncSession):
    """Criar limitação vinculada a uma diligência."""
    from datetime import datetime, timedelta
    from app.db.models.user import User
    from app.core.security import hash_password
    from app.schemas.diligence import DiligenceCreateRequest, DiligenceItemCreateRequest
    from app.services.diligence_service import create_diligence

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user2@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    diligence_payload = DiligenceCreateRequest(
        number="2024-TECH-001",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Documentos",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, diligence_payload)
    await db_session.commit()

    payload = TechnicalLimitationCreateRequest(
        type="escopo",
        description="Descrição",
        technical_impact="Impacto",
        criticality="alta",
        diligence_id=diligence.id,
    )

    limitation = await create_technical_limitation(db_session, case.id, payload)

    assert limitation.diligence_id == diligence.id


@pytest.mark.asyncio
async def test_read_technical_limitation(db_session: AsyncSession):
    """Obter limitação técnica existente."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user3@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    payload = TechnicalLimitationCreateRequest(
        type="escopo",
        description="Descrição",
        technical_impact="Impacto",
        criticality="crítica",
    )

    limitation = await create_technical_limitation(db_session, case.id, payload)
    await db_session.commit()

    read_limitation = await read_technical_limitation(db_session, limitation.id)

    assert read_limitation.id == limitation.id
    assert read_limitation.criticality == "crítica"


@pytest.mark.asyncio
async def test_read_technical_limitation_not_found(db_session: AsyncSession):
    """Erro ao obter limitação inexistente."""
    with pytest.raises(ValueError, match="Technical limitation .* not found"):
        await read_technical_limitation(db_session, "invalid-id")


@pytest.mark.asyncio
async def test_update_technical_limitation(db_session: AsyncSession):
    """Atualizar limitação técnica."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user4@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    payload = TechnicalLimitationCreateRequest(
        type="escopo",
        description="Descrição original",
        technical_impact="Impacto original",
        criticality="média",
    )

    limitation = await create_technical_limitation(db_session, case.id, payload)

    update_payload = TechnicalLimitationUpdateRequest(
        criticality="alta",
        status="active",
        description="Descrição atualizada",
    )

    updated = await update_technical_limitation(
        db_session, limitation.id, case.id, update_payload
    )

    assert updated.criticality == "alta"
    assert updated.status == "active"
    assert updated.description == "Descrição atualizada"


@pytest.mark.asyncio
async def test_delete_technical_limitation(db_session: AsyncSession):
    """Deletar limitação técnica."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user5@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    payload = TechnicalLimitationCreateRequest(
        type="escopo",
        description="Descrição",
        technical_impact="Impacto",
        criticality="média",
    )

    limitation = await create_technical_limitation(db_session, case.id, payload)
    limitation_id = limitation.id

    await delete_technical_limitation(db_session, limitation_id)

    with pytest.raises(ValueError, match="Technical limitation .* not found"):
        await read_technical_limitation(db_session, limitation_id)


@pytest.mark.asyncio
async def test_list_technical_limitations_by_case(db_session: AsyncSession):
    """Listar limitações técnicas de um processo."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user6@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    for i in range(3):
        payload = TechnicalLimitationCreateRequest(
            type="escopo",
            description=f"Descrição {i}",
            technical_impact="Impacto",
            criticality="média",
        )
        await create_technical_limitation(db_session, case.id, payload)

    limitations, total = await list_technical_limitations_by_case(db_session, case.id)

    assert total == 3
    assert len(limitations) == 3


@pytest.mark.asyncio
async def test_list_technical_limitations_filter_by_criticality(db_session: AsyncSession):
    """Listar limitações filtrando por criticidade."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user7@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    criticalities = ["baixa", "média", "alta", "crítica"]
    for crit in criticalities:
        payload = TechnicalLimitationCreateRequest(
            type="escopo",
            description=f"Descrição {crit}",
            technical_impact="Impacto",
            criticality=crit,
        )
        await create_technical_limitation(db_session, case.id, payload)

    high_limitations, high_total = await list_technical_limitations_by_case(
        db_session, case.id, criticality="alta"
    )

    assert high_total == 1
    assert len(high_limitations) == 1
    assert high_limitations[0].criticality == "alta"


@pytest.mark.asyncio
async def test_list_technical_limitations_pagination(db_session: AsyncSession):
    """Listar limitações com paginação."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user8@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    for i in range(5):
        payload = TechnicalLimitationCreateRequest(
            type="escopo",
            description=f"Descrição {i}",
            technical_impact="Impacto",
            criticality="média",
        )
        await create_technical_limitation(db_session, case.id, payload)

    page1, total1 = await list_technical_limitations_by_case(
        db_session, case.id, limit=2, offset=0
    )
    page2, total2 = await list_technical_limitations_by_case(
        db_session, case.id, limit=2, offset=2
    )

    assert len(page1) == 2
    assert len(page2) == 2
    assert total1 == 5
    assert total2 == 5


@pytest.mark.asyncio
async def test_create_limitation_with_invalid_diligence(db_session: AsyncSession):
    """Erro ao vincular diligência inexistente."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user9@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    payload = TechnicalLimitationCreateRequest(
        type="escopo",
        description="Descrição",
        technical_impact="Impacto",
        criticality="média",
        diligence_id="invalid-diligence",
    )

    with pytest.raises(ValueError, match="Diligence .* not found"):
        await create_technical_limitation(db_session, case.id, payload)


@pytest.mark.asyncio
async def test_create_limitation_all_criticalities(db_session: AsyncSession):
    """Criar limitações com todas as criticidades válidas."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="tech-user10@teste.com",
        full_name="Tech User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    criticalities = ["baixa", "média", "alta", "crítica"]

    for crit in criticalities:
        payload = TechnicalLimitationCreateRequest(
            type="escopo",
            description=f"Descrição {crit}",
            technical_impact="Impacto",
            criticality=crit,
        )

        limitation = await create_technical_limitation(db_session, case.id, payload)

        assert limitation.criticality == crit
