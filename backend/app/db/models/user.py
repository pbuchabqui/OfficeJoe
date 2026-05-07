"""
Modelo de usuário do sistema.

Responsável exclusivamente por identidade, credenciais e papel de acesso.
Não armazena dados periciais.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.db.models.role import Role
    from app.db.models.case import Case
    from app.db.models.audit_log import AuditLog


class User(Base, UUIDPrimaryKey, TimestampMixin):
    """
    Usuário autenticado no sistema.

    email            – identificador único de login.
    full_name        – nome completo para exibição e assinatura de laudo.
    hashed_password  – senha em bcrypt; nunca armazenada em texto claro.
    role             – FK textual para a tabela roles (ex: "perito").
                       Desnormalizado como VARCHAR para evitar joins em cada
                       requisição de autorização.
    is_active        – desativação sem exclusão física; mantém histórico de
                       auditoria intacto.
    otp_secret       – seed TOTP para 2FA (preparado; habilitado via otp_enabled).
    otp_enabled      – flag que ativa a exigência de OTP no login.
    last_login_at    – timestamp ISO do último login bem-sucedido.
    last_login_ip    – IP do último login; auxilia na detecção de acesso indevido.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # FK textual para roles — permite leitura direta sem join
    role: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("roles.name", ondelete="RESTRICT"),
        nullable=False,
        default="visualizador",
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 2FA — preparado para ativação futura
    otp_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    otp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Rastreamento de sessão
    last_login_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Relacionamentos
    role_ref: Mapped["Role"] = relationship("Role", back_populates="users")
    cases: Mapped[List["Case"]] = relationship(
        "Case", back_populates="responsible_user", lazy="dynamic"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
