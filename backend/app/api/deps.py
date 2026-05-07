"""
Dependências FastAPI: autenticação, autorização RBAC e persistência de auditoria.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, AuditEntry, log_audit
from app.core.config import get_settings
from app.core.security import Role, decode_token, has_permission
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.db.session import get_db

logger = logging.getLogger("officejoe.deps")
settings = get_settings()

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise JWTError("Subject vazio")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    return user


def require_permission(permission: str):
    """Factory que retorna uma dependência que verifica permissão RBAC."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        role = Role(user.role)
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão '{permission}' necessária.",
            )
        return user
    return _check


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def persist_audit(entry: AuditEntry, db: AsyncSession, case_id: Optional[str] = None) -> None:
    """Persiste uma entrada de auditoria no banco de dados."""
    try:
        log = AuditLog(
            id=entry.id,
            timestamp=entry.timestamp,
            action=entry.action.value,
            success=entry.success,
            user_id=entry.user_id,
            user_email=entry.user_email,
            ip_address=entry.ip_address,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            case_id=case_id,
            details=entry.details,
        )
        db.add(log)
        await db.flush()
    except Exception as exc:
        logger.error("Falha ao persistir auditoria: %s", exc)
