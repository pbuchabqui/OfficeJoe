"""
Testes unitários do serviço de cadeia de custódia.

Testa as funções do custody_service diretamente (sem camada HTTP),
usando o db_session em memória do conftest.
"""
from __future__ import annotations

import hashlib
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case, CaseStatus, CaseType
from app.db.models.custody_event import CustodyEvent, CustodyEventType
from app.db.models.document import File, IngestionStatus
from app.services.custody_service import (
    check_and_record_integrity,
    list_events_for_file,
    record_event,
    verify_file_integrity,
)


# ── fixtures locais ───────────────────────────────────────────────────────────

@pytest.fixture
def file_sha256():
    content = b"conteudo-do-arquivo-pericial-original"
    return hashlib.sha256(content).hexdigest()


@pytest.fixture
def different_sha256():
    return hashlib.sha256(b"conteudo-adulterado").hexdigest()


async def _make_file(db: AsyncSession, sha256: str, case_id: str) -> File:
    f = File(
        id=str(uuid.uuid4()),
        case_id=case_id,
        original_filename="laudo.pdf",
        sha256_hash=sha256,
        file_size_bytes=1024,
        mime_type="application/pdf",
        storage_bucket="officejoe-documents",
        storage_key=f"cases/{case_id}/files/test/laudo.pdf",
        ingestion_status=IngestionStatus.RECEIVED.value,
    )
    db.add(f)
    await db.flush()
    return f


async def _make_case(db: AsyncSession) -> Case:
    c = Case(
        id=str(uuid.uuid4()),
        case_number=f"{uuid.uuid4().int % 9999999:07d}-00.2024.5.02.0001",
        case_type=CaseType.TRABALHISTA.value,
        title="Caso Custódia Teste",
        status=CaseStatus.PLANEJAMENTO.value,
    )
    db.add(c)
    await db.flush()
    return c


# ── verify_file_integrity (função pura) ───────────────────────────────────────

def test_integrity_ok_when_hashes_match(file_sha256):
    assert verify_file_integrity(file_sha256, file_sha256) is True


def test_integrity_ok_case_insensitive(file_sha256):
    assert verify_file_integrity(file_sha256.upper(), file_sha256.lower()) is True


def test_integrity_fail_when_hashes_differ(file_sha256, different_sha256):
    assert verify_file_integrity(file_sha256, different_sha256) is False


def test_integrity_fail_on_empty_stored():
    assert verify_file_integrity("", "abc123") is False


def test_integrity_fail_on_empty_actual():
    assert verify_file_integrity("abc123", "") is False


def test_integrity_fail_on_both_empty():
    assert verify_file_integrity("", "") is False


# ── record_event (async, persiste no DB) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_record_event_upload(db_session: AsyncSession, file_sha256: str):
    case = await _make_case(db_session)
    file = await _make_file(db_session, file_sha256, case.id)

    event = await record_event(
        db_session,
        file_id=file.id,
        event_type=CustodyEventType.UPLOADED,
        actor_user_id=None,
        actor_ip="10.0.0.1",
        notes="Upload inicial via API",
    )

    assert event.id is not None
    assert event.file_id == file.id
    assert event.event_type == CustodyEventType.UPLOADED.value
    assert event.actor_ip == "10.0.0.1"
    assert event.event_at is not None
    assert event.integrity_ok is None  # não é evento de integridade


@pytest.mark.asyncio
async def test_record_event_is_persisted(db_session: AsyncSession, file_sha256: str):
    case = await _make_case(db_session)
    file = await _make_file(db_session, file_sha256, case.id)

    event = await record_event(
        db_session,
        file_id=file.id,
        event_type=CustodyEventType.HASH_CALCULATED,
    )

    result = await db_session.execute(
        select(CustodyEvent).where(CustodyEvent.id == event.id)
    )
    persisted = result.scalar_one_or_none()
    assert persisted is not None
    assert persisted.event_type == "hash_calculated"


@pytest.mark.asyncio
async def test_record_event_all_required_types(db_session: AsyncSession, file_sha256: str):
    """Todos os tipos obrigatórios do prompt devem ser registráveis."""
    case = await _make_case(db_session)
    file = await _make_file(db_session, file_sha256, case.id)

    required_types = [
        CustodyEventType.UPLOADED,
        CustodyEventType.HASH_CALCULATED,
        CustodyEventType.VIEWED,
        CustodyEventType.DOWNLOADED,
        CustodyEventType.DERIVED_CREATED,
        CustodyEventType.REPROCESSED,
        CustodyEventType.INTEGRITY_CHECKED,
    ]
    for event_type in required_types:
        event = await record_event(db_session, file_id=file.id, event_type=event_type)
        assert event.event_type == event_type.value, f"Falhou para {event_type.value}"


@pytest.mark.asyncio
async def test_record_event_immutable_no_updated_at():
    """CustodyEvent não deve ter updated_at — registro imutável."""
    columns = {c.key for c in CustodyEvent.__table__.columns}
    assert "updated_at" not in columns


# ── check_and_record_integrity ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_integrity_check_success(db_session: AsyncSession, file_sha256: str):
    case = await _make_case(db_session)
    file = await _make_file(db_session, file_sha256, case.id)

    ok, event = await check_and_record_integrity(
        db_session,
        file=file,
        actual_hash=file_sha256,
        actor_user_id=None,
        actor_ip="192.168.1.1",
    )

    assert ok is True
    assert event.event_type == CustodyEventType.INTEGRITY_CHECKED.value
    assert event.integrity_ok is True
    assert event.integrity_hash_verified == file_sha256
    assert event.notes is None


@pytest.mark.asyncio
async def test_integrity_check_failure(
    db_session: AsyncSession, file_sha256: str, different_sha256: str
):
    case = await _make_case(db_session)
    file = await _make_file(db_session, file_sha256, case.id)

    ok, event = await check_and_record_integrity(
        db_session,
        file=file,
        actual_hash=different_sha256,
    )

    assert ok is False
    assert event.event_type == CustodyEventType.INTEGRITY_FAIL.value
    assert event.integrity_ok is False
    assert event.integrity_hash_verified == different_sha256
    assert event.notes is not None  # deve ter nota explicando a falha


@pytest.mark.asyncio
async def test_integrity_fail_event_is_persisted(
    db_session: AsyncSession, file_sha256: str, different_sha256: str
):
    case = await _make_case(db_session)
    file = await _make_file(db_session, file_sha256, case.id)

    _, event = await check_and_record_integrity(
        db_session, file=file, actual_hash=different_sha256
    )

    result = await db_session.execute(
        select(CustodyEvent).where(CustodyEvent.id == event.id)
    )
    persisted = result.scalar_one_or_none()
    assert persisted is not None
    assert persisted.integrity_ok is False


# ── list_events_for_file ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_events_empty_for_new_file(db_session: AsyncSession, file_sha256: str):
    case = await _make_case(db_session)
    file = await _make_file(db_session, file_sha256, case.id)

    events = await list_events_for_file(db_session, file.id)
    assert events == []


@pytest.mark.asyncio
async def test_list_events_returns_in_chronological_order(
    db_session: AsyncSession, file_sha256: str
):
    case = await _make_case(db_session)
    file = await _make_file(db_session, file_sha256, case.id)

    await record_event(db_session, file_id=file.id, event_type=CustodyEventType.UPLOADED)
    await record_event(db_session, file_id=file.id, event_type=CustodyEventType.HASH_CALCULATED)
    await record_event(db_session, file_id=file.id, event_type=CustodyEventType.VIEWED)

    events = await list_events_for_file(db_session, file.id)
    assert len(events) == 3
    assert events[0].event_type == CustodyEventType.UPLOADED.value
    assert events[1].event_type == CustodyEventType.HASH_CALCULATED.value
    assert events[2].event_type == CustodyEventType.VIEWED.value
    # Verifica ordem ascendente
    for i in range(len(events) - 1):
        assert events[i].event_at <= events[i + 1].event_at


@pytest.mark.asyncio
async def test_list_events_isolated_per_file(db_session: AsyncSession, file_sha256: str):
    """Eventos de um arquivo não aparecem na listagem de outro."""
    case = await _make_case(db_session)
    file_a = await _make_file(db_session, file_sha256, case.id)
    file_b = await _make_file(db_session, file_sha256, case.id)

    await record_event(db_session, file_id=file_a.id, event_type=CustodyEventType.UPLOADED)
    await record_event(db_session, file_id=file_b.id, event_type=CustodyEventType.DOWNLOADED)

    events_a = await list_events_for_file(db_session, file_a.id)
    events_b = await list_events_for_file(db_session, file_b.id)

    assert len(events_a) == 1
    assert events_a[0].event_type == CustodyEventType.UPLOADED.value

    assert len(events_b) == 1
    assert events_b[0].event_type == CustodyEventType.DOWNLOADED.value


# ── enum coverage ─────────────────────────────────────────────────────────────

def test_all_required_event_types_exist():
    """Garante que os 7 tipos obrigatórios do prompt 9 existem no enum."""
    required = {
        "uploaded", "hash_calculated", "viewed", "downloaded",
        "derived_created", "reprocessed", "integrity_checked",
    }
    existing = {e.value for e in CustodyEventType}
    missing = required - existing
    assert not missing, f"Tipos obrigatórios ausentes: {missing}"
