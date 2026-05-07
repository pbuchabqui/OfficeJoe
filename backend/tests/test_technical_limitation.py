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
    create_limitation_from_diligence_item,
)
from app.db.models.diligence import Diligence
from app.db.models.diligence_item import DiligenceItem
from app.db.models.audit_log import AuditLog
from app.schemas.diligence import DiligenceCreateRequest, DiligenceItemCreateRequest
from app.services.diligence_service import create_diligence
from sqlalchemy import select
from datetime import datetime, timedelta


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


async def _make_diligence_with_items(
    db: AsyncSession, case_id: str
) -> tuple[Diligence, list[DiligenceItem]]:
    """Helper to create a diligence with items for testing."""
    deadline = datetime.utcnow() + timedelta(days=30)
    diligence_payload = DiligenceCreateRequest(
        number=f"DILIG-{uuid.uuid4().hex[:8]}",
        recipient="Test Recipient",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Documento Teste 1",
                period="2024-01 a 2024-03",
                technical_justification="Análise Técnica 1",
            ),
            DiligenceItemCreateRequest(
                requested_document="Documento Teste 2",
                period="2024-04 a 2024-06",
                technical_justification="Análise Técnica 2",
            ),
        ],
    )
    diligence = await create_diligence(db, case_id, diligence_payload)
    await db.commit()

    items = await db.scalars(
        select(DiligenceItem).where(DiligenceItem.diligence_id == diligence.id)
    )
    return diligence, items.all()


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


# ── Tests for create_limitation_from_diligence_item ────────────────────────────


@pytest.mark.asyncio
async def test_create_limitation_from_diligence_item_success(db_session: AsyncSession):
    """Criar limitação a partir de item de diligência não recebido com sucesso."""
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
    diligence, items = await _make_diligence_with_items(db_session, case.id)

    item = items[0]
    item.status_recebimento = "não_recebido"
    item.observacao_pendencia = "Cliente não respondeu à solicitação"
    db_session.add(item)
    await db_session.commit()

    limitation = await create_limitation_from_diligence_item(
        db_session, item.id, user.id
    )
    await db_session.commit()

    assert limitation.case_id == case.id
    assert limitation.type == "diligência_não_atendida"
    assert limitation.description == f"Documento não recebido: {item.requested_document}"
    assert limitation.technical_impact == "Cliente não respondeu à solicitação"
    assert limitation.criticality == "alta"
    assert limitation.status == "draft"
    assert limitation.diligence_id == diligence.id


@pytest.mark.asyncio
async def test_create_limitation_from_diligence_item_with_default_impact(
    db_session: AsyncSession,
):
    """Criar limitação usando mensagem padrão quando observação não está preenchida."""
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
    diligence, items = await _make_diligence_with_items(db_session, case.id)

    item = items[0]
    item.status_recebimento = "não_recebido"
    item.observacao_pendencia = None
    db_session.add(item)
    await db_session.commit()

    limitation = await create_limitation_from_diligence_item(
        db_session, item.id, user.id
    )
    await db_session.commit()

    assert (
        limitation.technical_impact
        == "Não foi possível obter o documento solicitado, impedindo análise técnica completa"
    )


@pytest.mark.asyncio
async def test_create_limitation_from_diligence_item_not_found(db_session: AsyncSession):
    """Erro ao criar limitação com item inexistente."""
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

    with pytest.raises(ValueError, match="Diligence item .* not found"):
        await create_limitation_from_diligence_item(db_session, "invalid-item", user.id)


@pytest.mark.asyncio
async def test_create_limitation_from_diligence_item_invalid_status_recebido(
    db_session: AsyncSession,
):
    """Erro ao criar limitação com item em status 'recebido'."""
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
    diligence, items = await _make_diligence_with_items(db_session, case.id)

    item = items[0]
    item.status_recebimento = "recebido"
    db_session.add(item)
    await db_session.commit()

    with pytest.raises(
        ValueError,
        match="Cannot create limitation: item status is recebido, expected 'não_recebido'",
    ):
        await create_limitation_from_diligence_item(db_session, item.id, user.id)


@pytest.mark.asyncio
async def test_create_limitation_from_diligence_item_invalid_status_parcial(
    db_session: AsyncSession,
):
    """Erro ao criar limitação com item em status 'parcial'."""
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
    diligence, items = await _make_diligence_with_items(db_session, case.id)

    item = items[0]
    item.status_recebimento = "parcial"
    db_session.add(item)
    await db_session.commit()

    with pytest.raises(
        ValueError,
        match="Cannot create limitation: item status is parcial, expected 'não_recebido'",
    ):
        await create_limitation_from_diligence_item(db_session, item.id, user.id)


@pytest.mark.asyncio
async def test_create_limitation_from_diligence_item_invalid_status_pendente(
    db_session: AsyncSession,
):
    """Erro ao criar limitação com item em status 'pendente'."""
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
    diligence, items = await _make_diligence_with_items(db_session, case.id)

    item = items[0]
    item.status_recebimento = "pendente"
    db_session.add(item)
    await db_session.commit()

    with pytest.raises(
        ValueError,
        match="Cannot create limitation: item status is pendente, expected 'não_recebido'",
    ):
        await create_limitation_from_diligence_item(db_session, item.id, user.id)


@pytest.mark.asyncio
async def test_create_limitation_from_diligence_item_audit_log(
    db_session: AsyncSession,
):
    """Verificar se auditoria é registrada ao criar limitação a partir de diligência."""
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
    diligence, items = await _make_diligence_with_items(db_session, case.id)

    item = items[0]
    item.status_recebimento = "não_recebido"
    item.observacao_pendencia = "Observação teste"
    db_session.add(item)
    await db_session.commit()

    limitation = await create_limitation_from_diligence_item(
        db_session, item.id, user.id
    )
    await db_session.commit()

    audit_logs = await db_session.scalars(
        select(AuditLog).where(
            (AuditLog.resource_type == "TechnicalLimitation")
            & (AuditLog.resource_id == limitation.id)
        )
    )
    logs = audit_logs.all()

    assert len(logs) == 1
    log = logs[0]
    assert log.action == "created_from_unmet_diligence"
    assert log.user_id == user.id
    assert log.details["diligence_item_id"] == item.id
    assert log.details["requested_document"] == item.requested_document
    assert log.details["diligence_id"] == diligence.id


@pytest.mark.asyncio
async def test_create_limitation_from_diligence_item_multiple_items(
    db_session: AsyncSession,
):
    """Criar limitações a partir de múltiplos itens de diligência não recebidos."""
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
    diligence, items = await _make_diligence_with_items(db_session, case.id)

    limitations = []
    for item in items:
        item.status_recebimento = "não_recebido"
        item.observacao_pendencia = f"Observação para {item.requested_document}"
        db_session.add(item)

    await db_session.commit()

    for item in items:
        limitation = await create_limitation_from_diligence_item(
            db_session, item.id, user.id
        )
        limitations.append(limitation)

    await db_session.commit()

    assert len(limitations) == 2
    for i, limitation in enumerate(limitations):
        assert limitation.description == f"Documento não recebido: {items[i].requested_document}"
        assert limitation.diligence_id == diligence.id
