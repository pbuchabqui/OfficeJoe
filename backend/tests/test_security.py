"""
Testes para segurança: JWT, hashing de senhas e RBAC.
"""
from __future__ import annotations

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


def test_refresh_token_rejected_as_access():
    """Refresh token não deve ser aceito como access token."""
    token = create_refresh_token(subject="user-789", role=Role.PERITO)
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["type"] != "access"


def test_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_token("token.invalido.qualquer")


def test_tampered_token_raises():
    token = create_access_token(subject="user-789", role=Role.LEITURA)
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
    assert has_permission(Role.PERITO, "evidence:validate") is True
    assert has_permission(Role.PERITO, "report:write") is True


def test_analista_can_write_documents():
    assert has_permission(Role.ANALISTA, "case:read") is True
    assert has_permission(Role.ANALISTA, "document:write") is True
    assert has_permission(Role.ANALISTA, "ocr:run") is True
    assert has_permission(Role.ANALISTA, "ai:query") is True


def test_analista_cannot_delete_or_validate():
    assert has_permission(Role.ANALISTA, "case:delete") is False
    assert has_permission(Role.ANALISTA, "document:delete") is False
    assert has_permission(Role.ANALISTA, "evidence:validate") is False
    assert has_permission(Role.ANALISTA, "ai:review") is False


def test_revisor_can_validate():
    assert has_permission(Role.REVISOR, "extraction:validate") is True
    assert has_permission(Role.REVISOR, "evidence:validate") is True
    assert has_permission(Role.REVISOR, "quesito:review") is True
    assert has_permission(Role.REVISOR, "ai:review") is True
    assert has_permission(Role.REVISOR, "audit:read") is True


def test_revisor_cannot_write():
    assert has_permission(Role.REVISOR, "case:write") is False
    assert has_permission(Role.REVISOR, "document:write") is False
    assert has_permission(Role.REVISOR, "quesito:write") is False


def test_leitura_cannot_write():
    assert has_permission(Role.LEITURA, "document:write") is False
    assert has_permission(Role.LEITURA, "case:delete") is False
    assert has_permission(Role.LEITURA, "ai:query") is False
    assert has_permission(Role.LEITURA, "ocr:run") is False


def test_leitura_can_read():
    assert has_permission(Role.LEITURA, "case:read") is True
    assert has_permission(Role.LEITURA, "document:read") is True
    assert has_permission(Role.LEITURA, "extraction:read") is True
    assert has_permission(Role.LEITURA, "evidence:read") is True
