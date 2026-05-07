"""Tests for evidence matrix validator."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case, CaseStatus, CaseType
from app.db.models.document import Document
from app.db.models.evidence_item import EvidenceItem
from app.db.models.evidence_matrix_item import EvidenceMatrixItem
from app.db.models.page import Page
from app.schemas.evidence_matrix import EvidenceMatrixCreateRequest
from app.schemas.evidence_matrix_validator import AlertLevel
from app.services.evidence_matrix_service import create_evidence_matrix
from app.services.evidence_matrix_validator_service import validate_matrix_item


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
    db: AsyncSession,
    case_id: str,
    doc_id: str,
    page_num: int,
    validation_status: str = "pending",
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
        validation_status=validation_status,
    )
    db.add(evidence)
    await db.flush()
    return evidence


# ── Validator Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_non_conclusive_item_no_alerts(db_session: AsyncSession):
    """Item não conclusivo não gera alertas bloqueantes."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="val-user1@teste.com",
        full_name="Validator User",
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
        disputed_fact="Fato controvertido",
        theme="Tema",
        evidence_ids=[evidence.id],
        status="draft",
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)
    await db_session.commit()

    result = await validate_matrix_item(db_session, matrix.id)

    assert result.is_valid is True
    assert len(result.alerts) == 0
    assert "não é conclusivo" in result.summary


@pytest.mark.asyncio
async def test_conclusive_with_validated_evidence_informativo(db_session: AsyncSession):
    """Item conclusivo com evidência validada gera alerta informativo."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="val-user2@teste.com",
        full_name="Validator User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)
    evidence = await _make_evidence(
        db_session, case.id, doc.id, 1, validation_status="validated"
    )

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Fato controvertido",
        theme="Tema",
        evidence_ids=[evidence.id],
        result_found="Resultado encontrado",
        technical_impact="Impacto técnico",
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)
    matrix.status = "published"
    await db_session.flush()
    await db_session.commit()

    result = await validate_matrix_item(db_session, matrix.id)

    assert result.is_valid is True
    informativo_alerts = [a for a in result.alerts if a.level == AlertLevel.INFORMATIVO]
    assert len(informativo_alerts) > 0
    assert "evidência(s) validada(s)" in informativo_alerts[0].message


@pytest.mark.asyncio
async def test_conclusive_without_evidence_bloqueante(db_session: AsyncSession):
    """Item conclusivo sem evidências gera alerta bloqueante."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="val-user3@teste.com",
        full_name="Validator User",
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
        disputed_fact="Fato controvertido",
        theme="Tema",
        evidence_ids=[evidence.id],
        result_found="Resultado encontrado",
        technical_impact="Impacto técnico",
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)
    matrix.status = "published"
    matrix.evidence_ids = []
    await db_session.flush()
    await db_session.commit()

    result = await validate_matrix_item(db_session, matrix.id)

    assert result.is_valid is False
    bloqueante_alerts = [a for a in result.alerts if a.level == AlertLevel.BLOQUEANTE]
    assert len(bloqueante_alerts) > 0
    assert "sem nenhuma evidência" in bloqueante_alerts[0].message


@pytest.mark.asyncio
async def test_conclusive_without_validated_evidence_critico(db_session: AsyncSession):
    """Item conclusivo sem evidências validadas gera alerta crítico."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="val-user4@teste.com",
        full_name="Validator User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)
    evidence = await _make_evidence(
        db_session, case.id, doc.id, 1, validation_status="pending"
    )

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Fato controvertido",
        theme="Tema",
        evidence_ids=[evidence.id],
        result_found="Resultado encontrado",
        technical_impact="Impacto técnico",
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)
    matrix.status = "published"
    await db_session.flush()
    await db_session.commit()

    result = await validate_matrix_item(db_session, matrix.id)

    assert result.is_valid is False
    critico_alerts = [a for a in result.alerts if a.level == AlertLevel.CRÍTICO]
    assert len(critico_alerts) > 0
    assert "sem nenhuma evidência validada" in critico_alerts[0].message


@pytest.mark.asyncio
async def test_conclusive_with_partial_validated_evidence_atencao(
    db_session: AsyncSession,
):
    """Item conclusivo com algumas evidências não validadas gera alerta atenção."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="val-user5@teste.com",
        full_name="Validator User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)
    evidence1 = await _make_evidence(
        db_session, case.id, doc.id, 1, validation_status="validated"
    )
    evidence2 = await _make_evidence(
        db_session, case.id, doc.id, 2, validation_status="pending"
    )
    evidence3 = await _make_evidence(
        db_session, case.id, doc.id, 3, validation_status="pending"
    )

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Fato controvertido",
        theme="Tema",
        evidence_ids=[evidence1.id, evidence2.id, evidence3.id],
        result_found="Resultado encontrado",
        technical_impact="Impacto técnico",
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)
    matrix.status = "published"
    await db_session.flush()
    await db_session.commit()

    result = await validate_matrix_item(db_session, matrix.id)

    assert result.is_valid is True
    atencao_alerts = [a for a in result.alerts if a.level == AlertLevel.ATENÇÃO]
    assert len(atencao_alerts) > 0
    assert "2 de 3 evidências não validadas" in atencao_alerts[0].message


@pytest.mark.asyncio
async def test_conclusive_multiple_alerts(db_session: AsyncSession):
    """Item conclusivo pode gerar múltiplos alertas."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="val-user6@teste.com",
        full_name="Validator User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)
    evidence1 = await _make_evidence(
        db_session, case.id, doc.id, 1, validation_status="validated"
    )
    evidence2 = await _make_evidence(
        db_session, case.id, doc.id, 2, validation_status="rejected"
    )

    payload = EvidenceMatrixCreateRequest(
        disputed_fact="Fato controvertido",
        theme="Tema",
        evidence_ids=[evidence1.id, evidence2.id],
        result_found="Resultado encontrado",
        technical_impact="Impacto técnico",
    )

    matrix = await create_evidence_matrix(db_session, case.id, payload)
    matrix.status = "published"
    await db_session.flush()
    await db_session.commit()

    result = await validate_matrix_item(db_session, matrix.id)

    assert result.is_valid is True
    assert len(result.alerts) > 1
    has_atencao = any(a.level == AlertLevel.ATENÇÃO for a in result.alerts)
    has_informativo = any(a.level == AlertLevel.INFORMATIVO for a in result.alerts)
    assert has_atencao or has_informativo


@pytest.mark.asyncio
async def test_matrix_item_not_found(db_session: AsyncSession):
    """Erro ao validar matriz inexistente."""
    with pytest.raises(ValueError, match="Matrix item .* not found"):
        await validate_matrix_item(db_session, "invalid-id")
