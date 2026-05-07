"""
Teste de criação das tabelas da migration 0001.

Verifica que os 6 modelos fundamentais criam suas tabelas corretamente
em banco SQLite em memória — sem dependência de PostgreSQL.

Testa:
- Criação das tabelas (schema)
- Inserção e leitura de registros
- Relacionamentos entre tabelas
- Invariantes de custódia (SHA-256, is_original_preserved)
- Imutabilidade dos registros de auditoria (sem updated_at)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    AuditLog,
    Case,
    CaseStatus,
    CaseType,
    CustodyEvent,
    CustodyEventType,
    File,
    IngestionStatus,
    Role,
    User,
)

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
        await s.rollback()


# ── Fixtures de dados base ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def role_perito(session: AsyncSession) -> Role:
    role = Role(
        name="perito",
        description="Perito responsável",
        permissions=["case:read", "case:write", "document:read", "document:write"],
    )
    session.add(role)
    await session.flush()
    return role


@pytest_asyncio.fixture
async def user_perito(session: AsyncSession, role_perito: Role) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email="perito@test.com",
        full_name="Perito Teste",
        hashed_password="$2b$12$hashed",
        role="perito",
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def case_trabalhista(session: AsyncSession, user_perito: User) -> Case:
    case = Case(
        id=str(uuid.uuid4()),
        case_number="0001234-56.2024.5.02.0001",
        case_type=CaseType.TRABALHISTA.value,
        title="Reclamação Trabalhista — Diferenças Salariais",
        status=CaseStatus.PLANEJAMENTO.value,
        court="2ª Vara do Trabalho de São Paulo",
        responsible_user_id=user_perito.id,
    )
    session.add(case)
    await session.flush()
    return case


@pytest_asyncio.fixture
async def sample_file(session: AsyncSession, case_trabalhista: Case, user_perito: User) -> File:
    file = File(
        id=str(uuid.uuid4()),
        case_id=case_trabalhista.id,
        original_filename="autos_processo.pdf",
        sha256_hash="a" * 64,
        file_size_bytes=10_485_760,  # 10 MB
        storage_bucket="officejoe-documents",
        storage_key=f"cases/{case_trabalhista.id}/files/doc001/autos_processo.pdf",
        ingestion_status=IngestionStatus.RECEIVED.value,
        uploaded_by_id=user_perito.id,
    )
    session.add(file)
    await session.flush()
    return file


# ── Testes de schema ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_six_tables_exist(engine):
    """Todas as 6 tabelas fundamentais devem existir após create_all."""
    expected = {"roles", "users", "cases", "files", "custody_events", "audit_logs"}
    async with engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
    assert expected.issubset(tables), f"Tabelas ausentes: {expected - tables}"


@pytest.mark.asyncio
async def test_audit_logs_has_no_updated_at(engine):
    """audit_logs não deve ter updated_at — registros são imutáveis."""
    async with engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: [
                c["name"] for c in inspect(sync_conn).get_columns("audit_logs")
            ]
        )
    assert "updated_at" not in columns
    assert "timestamp" in columns


@pytest.mark.asyncio
async def test_custody_events_has_no_updated_at(engine):
    """custody_events não deve ter updated_at — eventos são imutáveis."""
    async with engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: [
                c["name"] for c in inspect(sync_conn).get_columns("custody_events")
            ]
        )
    assert "updated_at" not in columns


# ── Testes de Role ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_role(session: AsyncSession):
    role = Role(
        name="admin",
        description="Administrador",
        permissions=["*"],
    )
    session.add(role)
    await session.flush()
    assert role.name == "admin"
    assert role.is_active is True


@pytest.mark.asyncio
async def test_role_permissions_are_list(role_perito: Role):
    assert isinstance(role_perito.permissions, list)
    assert "case:read" in role_perito.permissions


# ── Testes de User ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user(session: AsyncSession, role_perito: Role):
    user = User(
        id=str(uuid.uuid4()),
        email="novo@test.com",
        full_name="Novo Usuário",
        hashed_password="$2b$12$hashed_value",
        role="perito",
    )
    session.add(user)
    await session.flush()
    assert user.id is not None
    assert user.is_active is True
    assert user.otp_enabled is False


@pytest.mark.asyncio
async def test_user_email_is_unique(session: AsyncSession, user_perito: User):
    """Emails duplicados devem ser rejeitados pelo banco."""
    duplicate = User(
        id=str(uuid.uuid4()),
        email=user_perito.email,  # mesmo email
        full_name="Outro",
        hashed_password="$2b$12$other",
        role="perito",
    )
    session.add(duplicate)
    with pytest.raises(Exception):
        await session.flush()


# ── Testes de Case ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_case(case_trabalhista: Case):
    assert case_trabalhista.status == CaseStatus.PLANEJAMENTO.value
    assert case_trabalhista.case_type == CaseType.TRABALHISTA.value
    assert case_trabalhista.honorarium_proposed_cents is None


@pytest.mark.asyncio
async def test_case_number_is_unique(session: AsyncSession, case_trabalhista: Case):
    duplicate = Case(
        id=str(uuid.uuid4()),
        case_number=case_trabalhista.case_number,
        case_type=CaseType.CIVEL.value,
        title="Duplicata",
        status=CaseStatus.PLANEJAMENTO.value,
    )
    session.add(duplicate)
    with pytest.raises(Exception):
        await session.flush()


# ── Testes de File ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_file(sample_file: File):
    assert len(sample_file.sha256_hash) == 64
    assert sample_file.is_original_preserved is True
    assert sample_file.ingestion_status == IngestionStatus.RECEIVED.value


@pytest.mark.asyncio
async def test_file_original_preserved_is_true_by_default(sample_file: File):
    """Invariante fundamental: is_original_preserved deve ser sempre TRUE."""
    assert sample_file.is_original_preserved is True


@pytest.mark.asyncio
async def test_sha256_uniqueness_per_case(session: AsyncSession, sample_file: File):
    """O mesmo hash não pode aparecer duas vezes no mesmo processo."""
    duplicate = File(
        id=str(uuid.uuid4()),
        case_id=sample_file.case_id,
        original_filename="copia.pdf",
        sha256_hash=sample_file.sha256_hash,  # mesmo hash, mesmo processo
        file_size_bytes=100,
        storage_bucket="bucket",
        storage_key="other/path.pdf",
    )
    session.add(duplicate)
    with pytest.raises(Exception):
        await session.flush()


@pytest.mark.asyncio
async def test_sha256_same_hash_different_case_is_allowed(
    session: AsyncSession, sample_file: File, user_perito: User
):
    """O mesmo arquivo pode aparecer em processos distintos (cópias legítimas)."""
    other_case = Case(
        id=str(uuid.uuid4()),
        case_number="9999999-00.2024.5.02.0001",
        case_type=CaseType.CIVEL.value,
        title="Outro Processo",
        status=CaseStatus.PLANEJAMENTO.value,
    )
    session.add(other_case)
    await session.flush()

    file_other = File(
        id=str(uuid.uuid4()),
        case_id=other_case.id,
        original_filename=sample_file.original_filename,
        sha256_hash=sample_file.sha256_hash,
        file_size_bytes=sample_file.file_size_bytes,
        storage_bucket="bucket",
        storage_key="other/case/path.pdf",
    )
    session.add(file_other)
    await session.flush()  # Não deve lançar exceção
    assert file_other.id is not None


# ── Testes de CustodyEvent ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_custody_event_upload(
    session: AsyncSession, sample_file: File, user_perito: User
):
    event = CustodyEvent(
        id=str(uuid.uuid4()),
        file_id=sample_file.id,
        event_type=CustodyEventType.UPLOADED.value,
        event_at=datetime.now(timezone.utc),
        actor_user_id=user_perito.id,
        actor_ip="192.168.1.100",
    )
    session.add(event)
    await session.flush()
    assert event.integrity_ok is None  # não aplicável no upload


@pytest.mark.asyncio
async def test_create_custody_event_integrity_check(
    session: AsyncSession, sample_file: File
):
    event = CustodyEvent(
        id=str(uuid.uuid4()),
        file_id=sample_file.id,
        event_type=CustodyEventType.INTEGRITY_CHECK.value,
        event_at=datetime.now(timezone.utc),
        integrity_hash_verified=sample_file.sha256_hash,
        integrity_ok=True,
    )
    session.add(event)
    await session.flush()
    assert event.integrity_ok is True
    assert event.integrity_hash_verified == sample_file.sha256_hash


@pytest.mark.asyncio
async def test_integrity_fail_event(session: AsyncSession, sample_file: File):
    """Evento de falha de integridade deve ser registrável — é um alerta crítico."""
    event = CustodyEvent(
        id=str(uuid.uuid4()),
        file_id=sample_file.id,
        event_type=CustodyEventType.INTEGRITY_FAIL.value,
        event_at=datetime.now(timezone.utc),
        integrity_hash_verified="b" * 64,  # hash diferente
        integrity_ok=False,
        notes="Hash não confere. Possível adulteração.",
    )
    session.add(event)
    await session.flush()
    assert event.integrity_ok is False


# ── Testes de AuditLog ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_audit_log(
    session: AsyncSession, user_perito: User, case_trabalhista: Case
):
    log = AuditLog(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        action="document.upload",
        success=True,
        user_id=user_perito.id,
        user_email=user_perito.email,
        ip_address="10.0.0.1",
        case_id=case_trabalhista.id,
        resource_type="file",
        resource_id=str(uuid.uuid4()),
        details={"filename": "autos.pdf", "sha256": "a" * 64, "size_bytes": 1024},
    )
    session.add(log)
    await session.flush()
    assert log.id is not None
    assert log.success is True


@pytest.mark.asyncio
async def test_audit_log_failure_action(session: AsyncSession):
    """Logs de falha devem ser registráveis — essenciais para segurança."""
    log = AuditLog(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        action="auth.login_failure",
        success=False,
        user_email="hacker@externo.com",
        ip_address="203.0.113.42",
        details={"reason": "Senha incorreta", "attempts": 3},
    )
    session.add(log)
    await session.flush()
    assert log.success is False
    assert log.user_id is None  # usuário desconhecido


@pytest.mark.asyncio
async def test_audit_log_details_are_json(
    session: AsyncSession, user_perito: User
):
    payload = {
        "sha256": "a" * 64,
        "filename": "contrato.pdf",
        "size_bytes": 204_800,
    }
    log = AuditLog(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        action="document.upload",
        success=True,
        user_id=user_perito.id,
        user_email=user_perito.email,
        details=payload,
    )
    session.add(log)
    await session.flush()
    assert log.details["sha256"] == "a" * 64
