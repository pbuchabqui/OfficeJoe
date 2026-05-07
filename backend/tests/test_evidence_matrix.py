"""Tests for evidence matrix (proof matrix)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case, CaseStatus, CaseType
from app.db.models.document import Document
from app.db.models.evidence_item import EvidenceItem
from app.db.models.page import Page
from app.schemas.evidence_matrix import EvidenceMatrixCreateRequest
from app.services.evidence_matrix_service import (
    create_evidence_matrix,
    read_evidence_matrix,
    update_evidence_matrix,
    delete_evidence_matrix,
    list_evidence_matrix_by_case,
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


async def _make_document(db: AsyncSession, case_id: str) -> Document:
    """Helper to create a test document."""
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=case_id,
        original_filename="test.pdf",
        display_name="test.pdf",
        category="outro",
        sha256_hash="a" * 64,
        file_size_bytes=1024,
        mime_type="application/pdf",
        storage_bucket="test-bucket",
        storage_key="test-key",
        status="uploaded",
        is_original_preserved=True,
    )
    db.add(doc)
    await db.flush()
    return doc


async def _make_evidence(
    db: AsyncSession, case_id: str, doc_id: str, page_num: int
) -> EvidenceItem:
    """Helper to create a test evidence item."""
    page = Page(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        page_number=page_num,
        raw_text=f"Test page {page_num}",
    )
    db.add(page)
    await db.flush()

    evidence = EvidenceItem(
        case_id=case_id,
        document_id=doc_id,
        page_number=page_num,
        text_excerpt=f"Test evidence {page_num}",
        evidence_type="contrato",
        reliability_level=3,
        validation_status="pending",
    )
    db.add(evidence)
    await db.flush()
    return evidence


# ── Service Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_evidence_matrix_success(db_session: AsyncSession):
    """Criar matriz de prova com sucesso."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="matrix-user@teste.com",
        full_name="Matrix User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)
    evidence = await _make_evidence(db_session, case.id, doc.id, 1)

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Salário não foi pago",
        theme="Remuneração",
        evidence_ids=[evidence.id],
        expert_procedure="Análise de documentos",
        methodology_or_criteria="Comparação com contrato",
        result_found="Discrepância de 10%",
        technical_impact="Afeta cálculos",
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)

    assert matrix.case_id == case.id
    assert matrix.disputed_fact == "Salário não foi pago"
    assert matrix.theme == "Remuneração"
    assert matrix.evidence_ids == [evidence.id]
    assert matrix.status == "draft"


@pytest.mark.asyncio
async def test_create_evidence_matrix_without_evidence(db_session: AsyncSession):
    """Erro ao criar matriz sem evidências."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="List should have at least 1 item"):
        payload = EvidenceMatrixCreateRequest(
            disputed_fact="Salário não foi pago",
            theme="Remuneração",
            evidence_ids=[],
            expert_procedure="Análise de documentos",
        )


@pytest.mark.asyncio
async def test_create_evidence_matrix_invalid_evidence(db_session: AsyncSession):
    """Erro ao usar evidência inexistente."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="matrix-user3@teste.com",
        full_name="Matrix User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Salário não foi pago",
        theme="Remuneração",
        evidence_ids=["invalid-evidence-id"],
    )

    with pytest.raises(
        ValueError,
        match="Uma ou mais evidências não existem ou não pertencem ao caso",
    ):
        await create_evidence_matrix(db_session, case.id, payload)


@pytest.mark.asyncio
async def test_read_evidence_matrix_success(db_session: AsyncSession):
    """Ler matriz de prova com sucesso."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="matrix-user4@teste.com",
        full_name="Matrix User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)
    evidence = await _make_evidence(db_session, case.id, doc.id, 1)

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Teste",
        theme="Teste",
        evidence_ids=[evidence.id],
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)

    read_matrix = await read_evidence_matrix(db_session, matrix.id)

    assert read_matrix.id == matrix.id
    assert read_matrix.disputed_fact == "Teste"


@pytest.mark.asyncio
async def test_update_evidence_matrix_success(db_session: AsyncSession):
    """Atualizar matriz de prova."""
    from app.db.models.user import User
    from app.core.security import hash_password
    from app.schemas.evidence_matrix import EvidenceMatrixUpdateRequest

    user = User(
        id=str(uuid.uuid4()),
        email="matrix-user5@teste.com",
        full_name="Matrix User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)
    evidence = await _make_evidence(db_session, case.id, doc.id, 1)

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Antigo",
        theme="Teste",
        evidence_ids=[evidence.id],
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)

    update_payload = EvidenceMatrixUpdateRequest(
        disputed_fact="Novo",
        status="published",
    )

    updated = await update_evidence_matrix(db_session, matrix.id, case.id, update_payload)

    assert updated.disputed_fact == "Novo"
    assert updated.status == "published"


@pytest.mark.asyncio
async def test_delete_evidence_matrix_success(db_session: AsyncSession):
    """Deletar matriz de prova."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="matrix-user6@teste.com",
        full_name="Matrix User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)
    evidence = await _make_evidence(db_session, case.id, doc.id, 1)

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Teste",
        theme="Teste",
        evidence_ids=[evidence.id],
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)

    await delete_evidence_matrix(db_session, matrix.id)

    with pytest.raises(ValueError, match="Matrix item .* not found"):
        await read_evidence_matrix(db_session, matrix.id)


@pytest.mark.asyncio
async def test_list_evidence_matrix_empty(db_session: AsyncSession):
    """Listar matriz vazia."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="matrix-user7@teste.com",
        full_name="Matrix User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    items, total = await list_evidence_matrix_by_case(db_session, case.id)

    assert total == 0
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_evidence_matrix_pagination(db_session: AsyncSession):
    """Paginação da matriz de prova."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="matrix-user8@teste.com",
        full_name="Matrix User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)

    for i in range(5):
        evidence = await _make_evidence(db_session, case.id, doc.id, i + 1)
        payload = EvidenceMatrixCreateRequest(
            disputed_fact=f"Fato {i}",
            theme="Teste",
            evidence_ids=[evidence.id],
        )
        await create_evidence_matrix(db_session, case.id, payload)

    await db_session.commit()

    items, total = await list_evidence_matrix_by_case(db_session, case.id, limit=2, offset=0)

    assert total == 5
    assert len(items) == 2

    items, total = await list_evidence_matrix_by_case(db_session, case.id, limit=2, offset=2)

    assert total == 5
    assert len(items) == 2
