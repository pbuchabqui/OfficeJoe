"""Tests for quesitos module."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case, CaseStatus, CaseType
from app.db.models.quesito import Quesito, QuesitoStatus
from app.schemas.quesito import QuesitoCreate, QuesitoUpdate, QuesitoImportRequest, QuesitoImportItem


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
async def test_create_quesito_basic(db_session: AsyncSession):
    """Criar quesito básico."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="quesito-user1@teste.com",
        full_name="Quesito User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=case.id,
        sequence_number=1,
        origin="juizo",
        question_text="Qual foi a receita total em 2023?",
        tema="contábil",
        tipo="técnico",
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)
    await db_session.flush()

    assert quesito.id
    assert quesito.case_id == case.id
    assert quesito.sequence_number == 1
    assert quesito.tema == "contábil"
    assert quesito.tipo == "técnico"
    assert quesito.status == QuesitoStatus.PENDENTE.value


@pytest.mark.asyncio
async def test_create_quesito_multiple(db_session: AsyncSession):
    """Criar múltiplos quesitos com diferentes temas e tipos."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="quesito-user2@teste.com",
        full_name="Quesito User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    quesitos_data = [
        ("Qual foi a receita?", "contábil", "técnico"),
        ("Qual foi o custo?", "financeiro", "técnico"),
        ("Como foram classificadas as operações?", "contábil", "jurídico"),
    ]

    for seq, (texto, tema, tipo) in enumerate(quesitos_data, 1):
        quesito = Quesito(
            id=str(uuid.uuid4()),
            case_id=case.id,
            sequence_number=seq,
            origin="juizo",
            question_text=texto,
            tema=tema,
            tipo=tipo,
            status=QuesitoStatus.PENDENTE.value,
        )
        db_session.add(quesito)

    await db_session.flush()

    result = await db_session.execute(
        select(Quesito).where(Quesito.case_id == case.id).order_by(Quesito.sequence_number)
    )
    quesitos = result.scalars().all()

    assert len(quesitos) == 3
    assert quesitos[0].tema == "contábil"
    assert quesitos[1].tema == "financeiro"
    assert quesitos[2].tipo == "jurídico"


@pytest.mark.asyncio
async def test_quesito_with_optional_fields(db_session: AsyncSession):
    """Criar quesito com campos opcionais nulos."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="quesito-user3@teste.com",
        full_name="Quesito User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=case.id,
        sequence_number=1,
        origin="parte_autora",
        question_text="Qual foi a receita?",
        tema=None,
        tipo=None,
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)
    await db_session.flush()

    assert quesito.tema is None
    assert quesito.tipo is None
    assert quesito.origin == "parte_autora"


@pytest.mark.asyncio
async def test_update_quesito_fields(db_session: AsyncSession):
    """Atualizar campos de um quesito."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="quesito-user4@teste.com",
        full_name="Quesito User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=case.id,
        sequence_number=1,
        origin="juizo",
        question_text="Qual foi a receita?",
        tema="contábil",
        tipo="técnico",
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)
    await db_session.flush()

    quesito.tema = "financeiro"
    quesito.tipo = "jurídico"
    quesito.status = QuesitoStatus.EM_ANALISE.value
    await db_session.flush()

    assert quesito.tema == "financeiro"
    assert quesito.tipo == "jurídico"
    assert quesito.status == QuesitoStatus.EM_ANALISE.value


@pytest.mark.asyncio
async def test_list_quesitos_by_case(db_session: AsyncSession):
    """Listar quesitos de um caso."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="quesito-user5@teste.com",
        full_name="Quesito User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    for i in range(3):
        quesito = Quesito(
            id=str(uuid.uuid4()),
            case_id=case.id,
            sequence_number=i + 1,
            origin="juizo",
            question_text=f"Pergunta {i + 1}?",
            tema="contábil",
            tipo="técnico",
            status=QuesitoStatus.PENDENTE.value,
        )
        db_session.add(quesito)

    await db_session.flush()

    result = await db_session.execute(
        select(Quesito).where(Quesito.case_id == case.id).order_by(Quesito.sequence_number)
    )
    quesitos = result.scalars().all()

    assert len(quesitos) == 3
    assert quesitos[0].sequence_number == 1
    assert quesitos[2].sequence_number == 3


@pytest.mark.asyncio
async def test_quesito_status_transitions(db_session: AsyncSession):
    """Transições de status de quesito."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="quesito-user6@teste.com",
        full_name="Quesito User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=case.id,
        sequence_number=1,
        origin="juizo",
        question_text="Qual foi a receita?",
        tema="contábil",
        tipo="técnico",
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)
    await db_session.flush()

    assert quesito.status == QuesitoStatus.PENDENTE.value

    quesito.status = QuesitoStatus.EM_ANALISE.value
    await db_session.flush()
    assert quesito.status == QuesitoStatus.EM_ANALISE.value

    quesito.status = QuesitoStatus.RESPONDIDO.value
    await db_session.flush()
    assert quesito.status == QuesitoStatus.RESPONDIDO.value


# ── Endpoint Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_endpoint_create_quesito(client, perito_token, sample_case):
    """POST /cases/{case_id}/quesitos cria quesito."""
    payload = {
        "sequence_number": 1,
        "origin": "juizo",
        "question_text": "Qual foi a receita total?",
        "tema": "contábil",
        "tipo": "técnico",
    }

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/quesitos",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["question_text"] == "Qual foi a receita total?"
    assert data["tema"] == "contábil"
    assert data["tipo"] == "técnico"
    assert data["status"] == "pendente"


@pytest.mark.asyncio
async def test_endpoint_list_quesitos(client, perito_token, sample_case, db_session):
    """GET /cases/{case_id}/quesitos lista quesitos."""
    for i in range(3):
        quesito = Quesito(
            id=str(uuid.uuid4()),
            case_id=sample_case.id,
            sequence_number=i + 1,
            origin="juizo",
            question_text=f"Pergunta {i + 1}?",
            tema="contábil",
            tipo="técnico",
            status=QuesitoStatus.PENDENTE.value,
        )
        db_session.add(quesito)

    await db_session.commit()

    response = await client.get(
        f"/api/v1/cases/{sample_case.id}/quesitos",
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_endpoint_update_quesito(client, perito_token, sample_case, db_session):
    """PATCH /cases/{case_id}/quesitos/{quesito_id} atualiza quesito."""
    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        sequence_number=1,
        origin="juizo",
        question_text="Pergunta original?",
        tema="contábil",
        tipo="técnico",
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)
    await db_session.commit()

    payload = {
        "question_text": "Pergunta atualizada?",
        "tema": "financeiro",
        "tipo": "jurídico",
        "status": "em_analise",
    }

    response = await client.patch(
        f"/api/v1/cases/{sample_case.id}/quesitos/{quesito.id}",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["question_text"] == "Pergunta atualizada?"
    assert data["tema"] == "financeiro"
    assert data["tipo"] == "jurídico"
    assert data["status"] == "em_analise"


@pytest.mark.asyncio
async def test_endpoint_batch_import_quesitos(client, perito_token, sample_case):
    """POST /cases/{case_id}/quesitos/batch/import importa múltiplos quesitos."""
    payload = {
        "quesitos": [
            {
                "sequence_number": 1,
                "origin": "juizo",
                "question_text": "Pergunta 1?",
                "tema": "contábil",
                "tipo": "técnico",
            },
            {
                "sequence_number": 2,
                "origin": "parte_autora",
                "question_text": "Pergunta 2?",
                "tema": "financeiro",
                "tipo": "jurídico",
            },
            {
                "sequence_number": 3,
                "origin": "parte_re",
                "question_text": "Pergunta 3?",
                "tema": None,
                "tipo": None,
            },
        ]
    }

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/quesitos/batch/import",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
    assert data[0]["question_text"] == "Pergunta 1?"
    assert data[0]["tema"] == "contábil"
    assert data[1]["tema"] == "financeiro"
    assert data[2]["tema"] is None


@pytest.mark.asyncio
async def test_endpoint_batch_import_validation(client, perito_token, sample_case):
    """POST /cases/{case_id}/quesitos/batch/import valida entrada."""
    payload = {
        "quesitos": [
            {
                "sequence_number": 1,
                "origin": "juizo",
                "question_text": "Pergunta válida?",
            }
        ]
    }

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/quesitos/batch/import",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["tema"] is None
    assert data[0]["tipo"] is None


@pytest.mark.asyncio
async def test_endpoint_batch_import_case_not_found(client, perito_token):
    """POST /cases/{case_id}/quesitos/batch/import com caso inexistente retorna 404."""
    payload = {
        "quesitos": [
            {
                "sequence_number": 1,
                "origin": "juizo",
                "question_text": "Pergunta?",
                "tema": "contábil",
                "tipo": "técnico",
            }
        ]
    }

    response = await client.post(
        "/api/v1/cases/invalid-case/quesitos/batch/import",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_batch_import_empty(client, perito_token, sample_case):
    """POST /cases/{case_id}/quesitos/batch/import com lista vazia."""
    payload = {"quesitos": []}

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/quesitos/batch/import",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 0


# ── Evidence Linking Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_link_evidence_to_quesito(client, perito_token, sample_case, db_session):
    """POST /cases/{case_id}/quesitos/{quesito_id}/evidence vincula evidência."""
    from app.db.models.document import Document, DocumentStatus
    from app.db.models.evidence_item import EvidenceItem

    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        sequence_number=1,
        origin="juizo",
        question_text="Pergunta teste?",
        tema="contábil",
        tipo="técnico",
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)

    document = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        original_filename="test_doc.pdf",
        sha256_hash="abc123def456",
        file_size_bytes=1024,
        storage_bucket="test",
        storage_key="test/doc.pdf",
        status=DocumentStatus.INDEXED.value,
    )
    db_session.add(document)

    evidence = EvidenceItem(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        document_id=document.id,
        page_number=1,
        text_excerpt="Valor contestado",
        evidence_type="financial",
        reliability_level=3,
    )
    db_session.add(evidence)
    await db_session.flush()

    payload = {"evidence_item_id": evidence.id}

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/quesitos/{quesito.id}/evidence",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["quesito_id"] == quesito.id
    assert data["evidence_item_id"] == evidence.id
    assert data["evidence_item"]["id"] == evidence.id


@pytest.mark.asyncio
async def test_link_evidence_nonexistent_evidence(client, perito_token, sample_case, db_session):
    """POST /cases/{case_id}/quesitos/{quesito_id}/evidence com evidência inexistente retorna 404."""
    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        sequence_number=1,
        origin="juizo",
        question_text="Pergunta teste?",
        tema="contábil",
        tipo="técnico",
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)
    await db_session.flush()

    payload = {"evidence_item_id": str(uuid.uuid4())}

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/quesitos/{quesito.id}/evidence",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 404
    assert "Evidência não encontrada" in response.json()["detail"]


@pytest.mark.asyncio
async def test_link_evidence_nonexistent_quesito(client, perito_token, sample_case, db_session):
    """POST /cases/{case_id}/quesitos/{quesito_id}/evidence com quesito inexistente retorna 404."""
    from app.db.models.document import Document, DocumentStatus
    from app.db.models.evidence_item import EvidenceItem

    document = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        original_filename="test_doc.pdf",
        sha256_hash="abc123def456",
        file_size_bytes=1024,
        storage_bucket="test",
        storage_key="test/doc.pdf",
        status=DocumentStatus.INDEXED.value,
    )
    db_session.add(document)

    evidence = EvidenceItem(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        document_id=document.id,
        page_number=1,
        text_excerpt="Valor contestado",
        evidence_type="financial",
        reliability_level=3,
    )
    db_session.add(evidence)
    await db_session.flush()

    payload = {"evidence_item_id": evidence.id}

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/quesitos/{str(uuid.uuid4())}/evidence",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 404
    assert "Quesito não encontrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_link_evidence_from_different_case(client, perito_token, sample_case, db_session):
    """POST /cases/{case_id}/quesitos/{quesito_id}/evidence com evidência de outro caso retorna 400."""
    from app.db.models.case import Case, CaseStatus, CaseType
    from app.db.models.document import Document, DocumentStatus
    from app.db.models.evidence_item import EvidenceItem

    other_case = Case(
        id=str(uuid.uuid4()),
        case_number=f"{uuid.uuid4().hex[:7]}-56.2024.5.02.0001",
        case_type=CaseType.TRABALHISTA.value,
        title="Outro Caso",
        status=CaseStatus.PLANEJAMENTO.value,
        responsible_user_id=sample_case.responsible_user_id,
    )
    db_session.add(other_case)

    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        sequence_number=1,
        origin="juizo",
        question_text="Pergunta teste?",
        tema="contábil",
        tipo="técnico",
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)

    document = Document(
        id=str(uuid.uuid4()),
        case_id=other_case.id,
        original_filename="test_doc.pdf",
        sha256_hash="abc123def456",
        file_size_bytes=1024,
        storage_bucket="test",
        storage_key="test/doc.pdf",
        status=DocumentStatus.INDEXED.value,
    )
    db_session.add(document)

    evidence = EvidenceItem(
        id=str(uuid.uuid4()),
        case_id=other_case.id,
        document_id=document.id,
        page_number=1,
        text_excerpt="Valor contestado",
        evidence_type="financial",
        reliability_level=3,
    )
    db_session.add(evidence)
    await db_session.flush()

    payload = {"evidence_item_id": evidence.id}

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/quesitos/{quesito.id}/evidence",
        json=payload,
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 400
    assert "não pertence ao mesmo processo" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_quesito_evidence(client, perito_token, sample_case, db_session):
    """GET /cases/{case_id}/quesitos/{quesito_id}/evidence lista evidências."""
    from app.db.models.document import Document, DocumentStatus
    from app.db.models.evidence_item import EvidenceItem
    from app.db.models.question_evidence_link import QuestionEvidenceLink

    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        sequence_number=1,
        origin="juizo",
        question_text="Pergunta teste?",
        tema="contábil",
        tipo="técnico",
        status=QuesitoStatus.PENDENTE.value,
    )
    db_session.add(quesito)

    document = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        original_filename="test_doc.pdf",
        sha256_hash="abc123def456",
        file_size_bytes=1024,
        storage_bucket="test",
        storage_key="test/doc.pdf",
        status=DocumentStatus.INDEXED.value,
    )
    db_session.add(document)

    evidence1 = EvidenceItem(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        document_id=document.id,
        page_number=1,
        text_excerpt="Valor contestado",
        evidence_type="financial",
        reliability_level=3,
    )
    evidence2 = EvidenceItem(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        document_id=document.id,
        page_number=2,
        text_excerpt="Data do evento",
        evidence_type="temporal",
        reliability_level=2,
    )
    db_session.add(evidence1)
    db_session.add(evidence2)
    await db_session.flush()

    link1 = QuestionEvidenceLink(
        id=str(uuid.uuid4()),
        quesito_id=quesito.id,
        evidence_item_id=evidence1.id,
    )
    link2 = QuestionEvidenceLink(
        id=str(uuid.uuid4()),
        quesito_id=quesito.id,
        evidence_item_id=evidence2.id,
    )
    db_session.add(link1)
    db_session.add(link2)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/cases/{sample_case.id}/quesitos/{quesito.id}/evidence",
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == evidence1.id
    assert data[1]["id"] == evidence2.id
