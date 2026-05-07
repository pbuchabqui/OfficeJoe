"""
Endpoints de autenticação: login, refresh, criar usuário, perfil.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, persist_audit
from app.core.audit import AuditAction, log_audit
from app.core.config import get_settings
from app.core.security import (
    Role,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Autenticação"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    ip = get_client_ip(request)
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        entry = log_audit(
            action=AuditAction.LOGIN_FAILURE,
            user_email=payload.email,
            ip_address=ip,
            details={"reason": "Credenciais inválidas"},
            success=False,
        )
        await persist_audit(entry, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Contate o administrador.",
        )

    role = Role(user.role)
    access_token = create_access_token(subject=user.id, role=role)
    refresh_token = create_refresh_token(subject=user.id, role=role)

    # Atualiza último login
    user.last_login_at = datetime.now(timezone.utc).isoformat()
    user.last_login_ip = ip
    await db.flush()

    entry = log_audit(
        action=AuditAction.LOGIN_SUCCESS,
        user_id=user.id,
        user_email=user.email,
        ip_address=ip,
        details={"role": user.role},
    )
    await persist_audit(entry, db)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, request: Request) -> TokenResponse:
    from jose import JWTError
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise JWTError("Tipo de token inválido")
        user_id = data["sub"]
        role = Role(data["role"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    access_token = create_access_token(subject=user_id, role=role)
    new_refresh = create_refresh_token(subject=user_id, role=role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    if current_user.role not in (Role.ADMIN.value,):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores podem criar usuários.")

    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado.")

    import uuid
    user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.flush()

    entry = log_audit(
        action=AuditAction.USER_CREATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email, "role": user.role},
    )
    await persist_audit(entry, db)
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
