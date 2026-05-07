"""Tests for diligence document reception."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.case import Case, CaseStatus, CaseType
from app.db.models.document import Document
from app.db.models.diligence import Diligence
from app.db.models.diligence_item import DiligenceItem
from app.db.models.audit_log import AuditLog
from app.schemas.diligence import (
    DiligenceCreateRequest,
    DiligenceItemCreateRequest,
    DiligenceItemReceiptRequest,
)
from app.services.diligence_service import (
    create_diligence,
    register_document_receipt,
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


# ── Document Reception Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_document_receipt_success(db_session: AsyncSession):
    """Registrar recebimento de documento com sucesso."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="receipt-user1@teste.com",
        full_name="Receipt User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-RECEIPT-001",
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

    items = await db_session.scalars(
        select(DiligenceItem).where(DiligenceItem.diligence_id == diligence.id)
    )
    item = items.all()[0]

    receipt_payload = DiligenceItemReceiptRequest(
        documento_recebido_id=doc.id,
        status_recebimento="recebido",
        observacao_pendencia=None,
    )

    updated_item = await register_document_receipt(
        db_session, item.id, diligence.id, user.id, receipt_payload
    )
    await db_session.commit()

    assert updated_item.documento_recebido_id == doc.id
    assert updated_item.status_recebimento == "recebido"


@pytest.mark.asyncio
async def test_register_document_receipt_partial(db_session: AsyncSession):
    """Registrar recebimento parcial de documentos."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="receipt-user2@teste.com",
        full_name="Receipt User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-RECEIPT-002",
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

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    items = await db_session.scalars(
        select(DiligenceItem).where(DiligenceItem.diligence_id == diligence.id)
    )
    item = items.all()[0]

    receipt_payload = DiligenceItemReceiptRequest(
        documento_recebido_id=doc.id,
        status_recebimento="parcial",
        observacao_pendencia="Faltam recibos do período 02/2024",
    )

    updated_item = await register_document_receipt(
        db_session, item.id, diligence.id, user.id, receipt_payload
    )
    await db_session.commit()

    assert updated_item.status_recebimento == "parcial"
    assert updated_item.observacao_pendencia == "Faltam recibos do período 02/2024"


@pytest.mark.asyncio
async def test_register_document_receipt_not_received(db_session: AsyncSession):
    """Registrar documento não recebido."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="receipt-user3@teste.com",
        full_name="Receipt User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-RECEIPT-003",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Documento",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    items = await db_session.scalars(
        select(DiligenceItem).where(DiligenceItem.diligence_id == diligence.id)
    )
    item = items.all()[0]

    receipt_payload = DiligenceItemReceiptRequest(
        documento_recebido_id=doc.id,
        status_recebimento="não_recebido",
        observacao_pendencia="Destinatário não compareceu",
    )

    updated_item = await register_document_receipt(
        db_session, item.id, diligence.id, user.id, receipt_payload
    )
    await db_session.commit()

    assert updated_item.status_recebimento == "não_recebido"


@pytest.mark.asyncio
async def test_register_document_receipt_creates_audit_log(db_session: AsyncSession):
    """Registrar recebimento cria entrada em log de auditoria."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="receipt-user4@teste.com",
        full_name="Receipt User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-RECEIPT-004",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Documento",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    items = await db_session.scalars(
        select(DiligenceItem).where(DiligenceItem.diligence_id == diligence.id)
    )
    item = items.all()[0]

    receipt_payload = DiligenceItemReceiptRequest(
        documento_recebido_id=doc.id,
        status_recebimento="recebido",
    )

    await register_document_receipt(
        db_session, item.id, diligence.id, user.id, receipt_payload
    )
    await db_session.commit()

    audit_logs = await db_session.scalars(
        select(AuditLog).where(
            (AuditLog.resource_type == "DiligenceItem")
            & (AuditLog.resource_id == item.id)
            & (AuditLog.action == "document_received")
        )
    )

    logs = audit_logs.all()
    assert len(logs) > 0
    assert logs[0].user_id == user.id
    assert logs[0].details["documento_recebido_id"] == doc.id


@pytest.mark.asyncio
async def test_register_document_receipt_item_not_found(db_session: AsyncSession):
    """Erro ao registrar recebimento de item inexistente."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="receipt-user5@teste.com",
        full_name="Receipt User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)
    doc = await _make_document(db_session, case.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-RECEIPT-005",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Documento",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    receipt_payload = DiligenceItemReceiptRequest(
        documento_recebido_id=doc.id,
        status_recebimento="recebido",
    )

    with pytest.raises(ValueError, match="Item .* not found"):
        await register_document_receipt(
            db_session, "invalid-item-id", diligence.id, user.id, receipt_payload
        )


@pytest.mark.asyncio
async def test_register_document_receipt_document_not_found(db_session: AsyncSession):
    """Erro ao registrar com documento inexistente."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="receipt-user6@teste.com",
        full_name="Receipt User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-RECEIPT-006",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Documento",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case.id, payload)
    await db_session.commit()

    items = await db_session.scalars(
        select(DiligenceItem).where(DiligenceItem.diligence_id == diligence.id)
    )
    item = items.all()[0]

    receipt_payload = DiligenceItemReceiptRequest(
        documento_recebido_id="invalid-doc-id",
        status_recebimento="recebido",
    )

    with pytest.raises(ValueError, match="Document .* not found"):
        await register_document_receipt(
            db_session, item.id, diligence.id, user.id, receipt_payload
        )


@pytest.mark.asyncio
async def test_register_document_receipt_document_wrong_case(db_session: AsyncSession):
    """Erro ao vincular documento de outro processo."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="receipt-user7@teste.com",
        full_name="Receipt User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case1 = await _make_case(db_session, user.id)
    case2 = await _make_case(db_session, user.id)

    doc = await _make_document(db_session, case2.id)

    deadline = datetime.utcnow() + timedelta(days=30)
    payload = DiligenceCreateRequest(
        number="2024-RECEIPT-007",
        recipient="Cliente",
        deadline=deadline,
        items=[
            DiligenceItemCreateRequest(
                requested_document="Documento",
                period="2024-01 a 2024-03",
                technical_justification="Análise",
            )
        ],
    )

    diligence = await create_diligence(db_session, case1.id, payload)
    await db_session.commit()

    items = await db_session.scalars(
        select(DiligenceItem).where(DiligenceItem.diligence_id == diligence.id)
    )
    item = items.all()[0]

    receipt_payload = DiligenceItemReceiptRequest(
        documento_recebido_id=doc.id,
        status_recebimento="recebido",
    )

    with pytest.raises(ValueError, match="does not belong to case"):
        await register_document_receipt(
            db_session, item.id, diligence.id, user.id, receipt_payload
        )
