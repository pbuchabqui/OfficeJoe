"""
Testes de integração para endpoints de autenticação e bloqueio de rotas protegidas.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Login ─────────────────────────────────────────────────────────────────────

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
async def test_login_inactive_user(client: AsyncClient, inactive_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "inativo@teste.com",
        "password": "SenhaSegura123!",
    })
    assert response.status_code == 403


# ── Refresh ───────────────────────────────────────────────────────────────────

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
    assert "refresh_token" in response.json()


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client: AsyncClient, admin_user):
    """Access token não deve ser aceito no endpoint de refresh."""
    login = await client.post("/api/v1/auth/login", json={
        "email": "admin@teste.com",
        "password": "SenhaSegura123!",
    })
    access_token = login.json()["access_token"]

    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_token,
    })
    assert response.status_code == 401


# ── /me — rota protegida ──────────────────────────────────────────────────────

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
async def test_get_me_refresh_token_rejected(client: AsyncClient, admin_user):
    """Refresh token deve ser rejeitado em rotas que exigem access token."""
    login = await client.post("/api/v1/auth/login", json={
        "email": "admin@teste.com",
        "password": "SenhaSegura123!",
    })
    refresh_token = login.json()["refresh_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401


# ── Criação de usuário (RBAC) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_as_admin(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "novo@teste.com",
            "full_name": "Novo Usuário",
            "password": "SenhaSegura456!",
            "role": "leitura",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "novo@teste.com"
    assert data["role"] == "leitura"


@pytest.mark.asyncio
async def test_create_user_as_perito_forbidden(client: AsyncClient, perito_token: str):
    """Perito não pode criar usuários — apenas admin."""
    response = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "outro@teste.com",
            "full_name": "Outro",
            "password": "SenhaSegura456!",
            "role": "leitura",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_invalid_role(client: AsyncClient, admin_token: str):
    """Perfil inválido deve ser rejeitado com 422."""
    response = await client.post(
        "/api/v1/auth/users",
        json={
            "email": "invalido@teste.com",
            "full_name": "Inválido",
            "password": "SenhaSegura456!",
            "role": "superuser",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_user_all_valid_roles(client: AsyncClient, admin_token: str):
    """Todos os perfis válidos devem ser aceitos."""
    roles = ["perito", "analista", "revisor", "leitura"]
    for i, role in enumerate(roles):
        response = await client.post(
            "/api/v1/auth/users",
            json={
                "email": f"user_{role}@teste.com",
                "full_name": f"Usuário {role}",
                "password": "SenhaSegura456!",
                "role": role,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201, f"Role '{role}' falhou: {response.json()}"
        assert response.json()["role"] == role
