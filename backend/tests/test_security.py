"""
Testes para segurança: JWT, hashing de senhas e RBAC.
"""
from __future__ import annotations

import time
import pytest
from jose import JWTError

from app.core.security import (
    Role,
    create_access_token,
    create_refresh_token,
    decode_token,
    has_permission,
    hash_password,
    verify_password,
)


# ── Senhas ────────────────────────────────────────────────────────────────────

def test_hash_password_not_plain():
    plain = "SenhaSegura123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert len(hashed) > 20


def test_verify_password_correct():
    plain = "SenhaSegura123!"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("SenhaCorreta")
    assert verify_password("SenhaErrada", hashed) is False


def test_different_hashes_same_password():
    # bcrypt usa salt aleatório: mesmo plain deve gerar hashes diferentes
    h1 = hash_password("mesma_senha")
    h2 = hash_password("mesma_senha")
    assert h1 != h2
    assert verify_password("mesma_senha", h1)
    assert verify_password("mesma_senha", h2)


# ── JWT ───────────────────────────────────────────────────────────────────────

def test_create_and_decode_access_token():
    token = create_access_token(subject="user-123", role=Role.PERITO)
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == Role.PERITO.value
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    token = create_refresh_token(subject="user-456", role=Role.ADMIN)
    payload = decode_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_token("token.invalido.qualquer")


def test_tampered_token_raises():
    token = create_access_token(subject="user-789", role=Role.VISUALIZADOR)
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(JWTError):
        decode_token(tampered)


# ── RBAC ─────────────────────────────────────────────────────────────────────

def test_admin_has_all_permissions():
    assert has_permission(Role.ADMIN, "document:delete") is True
    assert has_permission(Role.ADMIN, "user:create") is True
    assert has_permission(Role.ADMIN, "qualquer:permissao") is True


def test_perito_permissions():
    assert has_permission(Role.PERITO, "case:read") is True
    assert has_permission(Role.PERITO, "document:write") is True
    assert has_permission(Role.PERITO, "ai:query") is True


def test_visualizador_cannot_write():
    assert has_permission(Role.VISUALIZADOR, "document:write") is False
    assert has_permission(Role.VISUALIZADOR, "case:delete") is False
    assert has_permission(Role.VISUALIZADOR, "ai:query") is False


def test_visualizador_can_read():
    assert has_permission(Role.VISUALIZADOR, "case:read") is True
    assert has_permission(Role.VISUALIZADOR, "document:read") is True


def test_assistente_cannot_delete():
    assert has_permission(Role.ASSISTENTE, "case:delete") is False
    assert has_permission(Role.ASSISTENTE, "document:delete") is False
