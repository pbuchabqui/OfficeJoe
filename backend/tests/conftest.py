"""
Fixtures compartilhadas para os testes.
Usa banco SQLite em memória para isolamento (sem dependência de PostgreSQL nos testes unitários).
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import Role, create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Usuários de teste ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    from app.db.models.user import User
    user = User(
        id=str(uuid.uuid4()),
        email="admin@teste.com",
        full_name="Administrador Teste",
        hashed_password=hash_password("SenhaSegura123!"),
        role=Role.ADMIN.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def perito_user(db_session: AsyncSession):
    from app.db.models.user import User
    user = User(
        id=str(uuid.uuid4()),
        email="perito@teste.com",
        full_name="Perito Teste",
        hashed_password=hash_password("SenhaSegura123!"),
        role=Role.PERITO.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def analista_user(db_session: AsyncSession):
    from app.db.models.user import User
    user = User(
        id=str(uuid.uuid4()),
        email="analista@teste.com",
        full_name="Analista Teste",
        hashed_password=hash_password("SenhaSegura123!"),
        role=Role.ANALISTA.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def revisor_user(db_session: AsyncSession):
    from app.db.models.user import User
    user = User(
        id=str(uuid.uuid4()),
        email="revisor@teste.com",
        full_name="Revisor Teste",
        hashed_password=hash_password("SenhaSegura123!"),
        role=Role.REVISOR.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def leitura_user(db_session: AsyncSession):
    from app.db.models.user import User
    user = User(
        id=str(uuid.uuid4()),
        email="leitura@teste.com",
        full_name="Leitura Teste",
        hashed_password=hash_password("SenhaSegura123!"),
        role=Role.LEITURA.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession):
    from app.db.models.user import User
    user = User(
        id=str(uuid.uuid4()),
        email="inativo@teste.com",
        full_name="Usuário Inativo",
        hashed_password=hash_password("SenhaSegura123!"),
        role=Role.LEITURA.value,
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ── Tokens ────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_token(admin_user) -> str:
    return create_access_token(subject=admin_user.id, role=Role.ADMIN)


@pytest_asyncio.fixture
async def perito_token(perito_user) -> str:
    return create_access_token(subject=perito_user.id, role=Role.PERITO)


@pytest_asyncio.fixture
async def analista_token(analista_user) -> str:
    return create_access_token(subject=analista_user.id, role=Role.ANALISTA)


@pytest_asyncio.fixture
async def revisor_token(revisor_user) -> str:
    return create_access_token(subject=revisor_user.id, role=Role.REVISOR)


@pytest_asyncio.fixture
async def leitura_token(leitura_user) -> str:
    return create_access_token(subject=leitura_user.id, role=Role.LEITURA)


# ── Caso de teste ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def sample_case(db_session: AsyncSession, perito_user):
    from app.db.models.case import Case, CaseStatus, CaseType
    case = Case(
        id=str(uuid.uuid4()),
        case_number="0001234-56.2024.5.02.0001",
        case_type=CaseType.TRABALHISTA.value,
        title="Reclamação Trabalhista - Teste",
        status=CaseStatus.PLANEJAMENTO.value,
        responsible_user_id=perito_user.id,
    )
    db_session.add(case)
    await db_session.flush()
    return case
