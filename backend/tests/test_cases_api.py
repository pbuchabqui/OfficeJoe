"""
Testes de integração para endpoints de processos periciais.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


VALID_CASE = {
    "case_number": "9999999-00.2024.5.02.0099",
    "case_type": "trabalhista",
    "title": "Caso de Teste de Integração",
    "description": "Processo de teste automatizado",
    "court": "1ª Vara do Trabalho de São Paulo",
    "parties": [
        {"name": "Empresa Teste S.A.", "role": "reclamado"},
        {"name": "Trabalhador Teste", "role": "reclamante"},
    ],
}


@pytest.mark.asyncio
async def test_create_case(client: AsyncClient, perito_token: str):
    response = await client.post(
        "/api/v1/cases",
        json=VALID_CASE,
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["case_number"] == VALID_CASE["case_number"]
    assert data["status"] == "planejamento"
    assert len(data["parties"]) == 2


@pytest.mark.asyncio
async def test_create_duplicate_case(client: AsyncClient, perito_token: str, sample_case):
    response = await client.post(
        "/api/v1/cases",
        json={**VALID_CASE, "case_number": sample_case.case_number},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_cases(client: AsyncClient, perito_token: str, sample_case):
    response = await client.get(
        "/api/v1/cases",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_case(client: AsyncClient, perito_token: str, sample_case):
    response = await client.get(
        f"/api/v1/cases/{sample_case.id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_case.id


@pytest.mark.asyncio
async def test_get_case_not_found(client: AsyncClient, perito_token: str):
    response = await client.get(
        "/api/v1/cases/id-inexistente",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_case_status(client: AsyncClient, perito_token: str, sample_case):
    response = await client.patch(
        f"/api/v1/cases/{sample_case.id}",
        json={"status": "diligencias"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "diligencias"


@pytest.mark.asyncio
async def test_visualizador_cannot_create_case(client: AsyncClient, db_session):
    from app.core.security import Role, create_access_token, hash_password
    from app.db.models.user import User
    import uuid

    viewer = User(
        id=str(uuid.uuid4()),
        email="viewer@teste.com",
        full_name="Visualizador",
        hashed_password=hash_password("senha123"),
        role=Role.VISUALIZADOR.value,
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.flush()
    token = create_access_token(subject=viewer.id, role=Role.VISUALIZADOR)

    response = await client.post(
        "/api/v1/cases",
        json=VALID_CASE,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
