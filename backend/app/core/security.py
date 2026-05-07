"""
Segurança: hashing de senhas, geração/validação de tokens JWT, RBAC.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


# ── Roles / Permissões ────────────────────────────────────────────────────────

class Role(str, Enum):
    ADMIN = "admin"
    PERITO = "perito"
    ASSISTENTE = "assistente"
    VISUALIZADOR = "visualizador"


ROLE_PERMISSIONS: Dict[Role, List[str]] = {
    Role.ADMIN: ["*"],
    Role.PERITO: [
        "case:read", "case:write", "case:delete",
        "document:read", "document:write", "document:delete",
        "ocr:run", "extraction:read", "extraction:write",
        "quesito:read", "quesito:write",
        "ai:query", "ai:review",
        "evidence:read", "evidence:write",
        "audit:read",
    ],
    Role.ASSISTENTE: [
        "case:read", "case:write",
        "document:read", "document:write",
        "ocr:run", "extraction:read",
        "quesito:read",
        "evidence:read",
        "ai:query",
    ],
    Role.VISUALIZADOR: [
        "case:read",
        "document:read",
        "extraction:read",
        "quesito:read",
        "evidence:read",
    ],
}


def has_permission(role: Role, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms


# ── Senha ─────────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    subject: str,
    role: Role,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    expire = _now_utc() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "iat": _now_utc(),
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, role: Role) -> str:
    expire = _now_utc() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "iat": _now_utc(),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decodifica e valida JWT. Lança JWTError em caso de falha."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def get_token_subject(token: str) -> str:
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise JWTError("Token sem subject")
    return sub


def get_token_role(token: str) -> Role:
    payload = decode_token(token)
    role_str = payload.get("role")
    try:
        return Role(role_str)
    except ValueError:
        raise JWTError(f"Role inválida no token: {role_str}")
