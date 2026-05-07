"""
Testes de integração para endpoints de autenticação.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@teste.com",
        "password": "SenhaSegura123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@teste.com",
        "password": "SenhaErrada",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={
        "email": "naoexiste@teste.com",
        "password": "qualquer",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@teste.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token.invalido"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, admin_user):
    login = await client.post("/api/v1/auth/login", json={
        "email": "admin@teste.com",
        "password": "SenhaSegura123!",
    })
    refresh_token = login.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_create_user_as_admin(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "novo@teste.com",
            "full_name": "Novo Usuário",
            "password": "SenhaSegura456!",
            "role": "visualizador",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "novo@teste.com"


@pytest.mark.asyncio
async def test_create_user_as_non_admin(client: AsyncClient, perito_token: str):
    response = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "outro@teste.com",
            "full_name": "Outro",
            "password": "SenhaSegura456!",
            "role": "visualizador",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 403
