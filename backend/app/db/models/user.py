"""
Modelo de usuário com RBAC.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey
from app.core.security import Role


class User(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=Role.VISUALIZADOR.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    otp_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    otp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Relacionamentos
    audit_logs: Mapped[List["AuditLog"]] = relationship(  # noqa: F821
        "AuditLog", back_populates="user", lazy="dynamic"
    )
    cases: Mapped[List["Case"]] = relationship(  # noqa: F821
        "Case", back_populates="responsible_user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
