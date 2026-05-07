from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_and_get_current_user(client: AsyncClient, admin_user):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@teste.com", "password": "SenhaSegura123!"},
    )

    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "admin@teste.com"


@pytest.mark.asyncio
async def test_login_rejects_invalid_password(client: AsyncClient, admin_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@teste.com", "password": "senha-incorreta"},
    )

    assert response.status_code == 401
