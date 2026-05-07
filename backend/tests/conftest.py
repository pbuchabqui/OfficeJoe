"""
Fixtures compartilhadas para os testes.
Usa banco SQLite em memória para isolamento (sem dependência de PostgreSQL nos testes unitários).
"""
from __future__ import annotations

import asyncio
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
        email=f"perito-{uuid.uuid4()}@teste.com",
        full_name="Perito Teste",
        hashed_password=hash_password("SenhaSegura123!"),
        role=Role.PERITO.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def admin_token(admin_user) -> str:
    return create_access_token(subject=admin_user.id, role=Role.ADMIN)


@pytest.fixture
def perito_token(perito_user) -> str:
    return create_access_token(subject=perito_user.id, role=Role.PERITO)


@pytest_asyncio.fixture
async def sample_case(db_session: AsyncSession, perito_user):
    from app.db.models.case import Case, CaseStatus, CaseType
    case_num = f"{uuid.uuid4().hex[:7]}-56.2024.5.02.0001"
    case = Case(
        id=str(uuid.uuid4()),
        case_number=case_num,
        case_type=CaseType.TRABALHISTA.value,
        title="Reclamação Trabalhista - Teste",
        status=CaseStatus.PLANEJAMENTO.value,
        responsible_user_id=perito_user.id,
    )
    db_session.add(case)
    await db_session.flush()
    return case
