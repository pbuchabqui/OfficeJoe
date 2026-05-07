from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Senha não pode ser vazia.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class RefreshRequest(BaseModel):
    refresh_token: str


_VALID_ROLES = {"admin", "perito", "analista", "revisor", "leitura"}


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "leitura"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter ao menos 8 caracteres.")
        return v

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_ROLES:
            raise ValueError(f"Perfil inválido. Opções: {', '.join(sorted(_VALID_ROLES))}")
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    otp_enabled: bool

    model_config = {"from_attributes": True}
