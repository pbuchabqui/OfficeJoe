"""Tests for evidence creation and management."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.evidence import EvidenceType, ReliabilityLevel
from app.db.models.document import Document
from app.db.models.evidence_item import EvidenceItem
from app.db.models.page import Page
from app.schemas.evidence import EvidenceCreateRequest, CoordinatesSchema
from app.services.evidence_service import create_evidence, list_evidence_by_case


# ── Service Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_evidence_success(db_session: AsyncSession, sample_case):
    """Criar evidência com dados válidos."""
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
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
    db_session.add(doc)
    await db_session.flush()

    page = Page(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page_number=1,
        raw_text="Salário base R$ 2.500,00",
        ocr_confidence=0.95,
    )
    db_session.add(page)
    await db_session.flush()

    payload = EvidenceCreateRequest(
        document_id=doc.id,
        page_number=1,
        text_excerpt="Salário base R$ 2.500,00",
        evidence_type=EvidenceType.HOLERITE,
        notes="Extraído da página 1",
        reliability_level=ReliabilityLevel.ALTA,
    )

    evidence = await create_evidence(db_session, sample_case.id, payload)

    assert evidence.case_id == sample_case.id
    assert evidence.document_id == doc.id
    assert evidence.page_number == 1
    assert evidence.text_excerpt == "Salário base R$ 2.500,00"
    assert evidence.evidence_type == "holerite"
    assert evidence.reliability_level == 4
    assert evidence.validated is False


@pytest.mark.asyncio
async def test_create_evidence_with_coordinates(db_session: AsyncSession, sample_case):
    """Criar evidência com coordenadas."""
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
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
    db_session.add(doc)
    await db_session.flush()

    page = Page(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page_number=1,
        raw_text="Teste",
    )
    db_session.add(page)
    await db_session.flush()

    coords = CoordinatesSchema(x=100, y=150, width=200, height=50)
    payload = EvidenceCreateRequest(
        document_id=doc.id,
        page_number=1,
        text_excerpt="Teste",
        coordinates=coords,
        evidence_type=EvidenceType.CONTRATO,
    )

    evidence = await create_evidence(db_session, sample_case.id, payload)

    assert evidence.coordinates is not None
    assert evidence.coordinates["x"] == 100
    assert evidence.coordinates["y"] == 150


@pytest.mark.asyncio
async def test_create_evidence_case_not_found(db_session: AsyncSession):
    """Erro se processo não existe."""
    payload = EvidenceCreateRequest(
        document_id="invalid-doc",
        page_number=1,
        text_excerpt="Teste",
        evidence_type=EvidenceType.CONTRATO,
    )

    with pytest.raises(ValueError, match="Case .* not found"):
        await create_evidence(db_session, "invalid-case", payload)


@pytest.mark.asyncio
async def test_create_evidence_document_not_found(db_session: AsyncSession, sample_case):
    """Erro se documento não existe."""
    payload = EvidenceCreateRequest(
        document_id="invalid-doc",
        page_number=1,
        text_excerpt="Teste",
        evidence_type=EvidenceType.CONTRATO,
    )

    with pytest.raises(ValueError, match="Document .* not found"):
        await create_evidence(db_session, sample_case.id, payload)


@pytest.mark.asyncio
async def test_create_evidence_document_wrong_case(db_session: AsyncSession, sample_case):
    """Erro se documento não pertence ao processo."""
    other_case_id = str(uuid.uuid4())
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=other_case_id,
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
    db_session.add(doc)
    await db_session.flush()

    payload = EvidenceCreateRequest(
        document_id=doc.id,
        page_number=1,
        text_excerpt="Teste",
        evidence_type=EvidenceType.CONTRATO,
    )

    with pytest.raises(ValueError, match="not found in case"):
        await create_evidence(db_session, sample_case.id, payload)


@pytest.mark.asyncio
async def test_create_evidence_page_not_found(db_session: AsyncSession, sample_case):
    """Erro se página não existe no documento."""
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
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
    db_session.add(doc)
    await db_session.flush()

    payload = EvidenceCreateRequest(
        document_id=doc.id,
        page_number=999,
        text_excerpt="Teste",
        evidence_type=EvidenceType.CONTRATO,
    )

    with pytest.raises(ValueError, match="Page .* not found"):
        await create_evidence(db_session, sample_case.id, payload)


@pytest.mark.asyncio
async def test_list_evidence_empty(db_session: AsyncSession, sample_case):
    """Listar evidências de processo vazio."""
    items, total = await list_evidence_by_case(db_session, sample_case.id)
    assert total == 0
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_evidence_pagination(db_session: AsyncSession, sample_case):
    """Paginação funciona corretamente."""
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
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
    db_session.add(doc)
    await db_session.flush()

    page = Page(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        page_number=1,
        raw_text="Teste",
    )
    db_session.add(page)
    await db_session.flush()

    for i in range(5):
        evidence = EvidenceItem(
            case_id=sample_case.id,
            document_id=doc.id,
            page_number=1,
            text_excerpt=f"Evidence {i}",
            evidence_type="contrato",
            reliability_level=3,
        )
        db_session.add(evidence)

    await db_session.commit()

    items, total = await list_evidence_by_case(db_session, sample_case.id, limit=2, offset=0)
    assert total == 5
    assert len(items) == 2

    items, total = await list_evidence_by_case(db_session, sample_case.id, limit=2, offset=2)
    assert total == 5
    assert len(items) == 2


