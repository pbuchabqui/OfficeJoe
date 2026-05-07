"""
Tabela de referência de papéis (roles).

Mantida como tabela real em vez de enum puro para permitir
expansão de permissões sem migration de schema.
"""
from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, List

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class Role(Base, TimestampMixin):
    """
    Papel de acesso no sistema.

    name        – chave de negócio (admin, perito, analista, revisor, leitura).
                  Usada como FK textual em users.role para consultas legíveis
                  sem join.
    description – explicação em linguagem natural do papel.
    permissions – lista JSON de permissões granulares concedidas ao papel.
                  Ex: ["case:read", "document:write", "ocr:run"].
                  O papel "admin" recebe ["*"] para acesso irrestrito.
    is_active   – permite desativar um papel sem excluí-lo.
    """

    __tablename__ = "roles"

    # PK textual — evita joins desnecessários; valor é a própria chave de negócio
    name: Mapped[str] = mapped_column(String(30), primary_key=True)

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relacionamento reverso para auditoria
    users: Mapped[List["User"]] = relationship(
        "User", back_populates="role_ref", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Role name={self.name}>"


# Roles padrão do sistema — usados pela migration de seed
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Administrador do sistema — acesso irrestrito",
        "permissions": ["*"],
    },
    {
        "name": "perito",
        "description": "Perito responsável pelo processo — acesso completo ao processo",
        "permissions": [
            "case:read", "case:write", "case:delete",
            "document:read", "document:write", "document:delete",
            "ocr:run",
            "extraction:read", "extraction:write",
            "evidence:read", "evidence:write", "evidence:validate",
            "quesito:read", "quesito:write",
            "calc:read", "calc:write",
            "report:read", "report:write",
            "ai:query", "ai:review",
            "audit:read",
        ],
    },
    {
        "name": "analista",
        "description": "Analista do perito — leitura e escrita, sem validação e laudo",
        "permissions": [
            "case:read", "case:write",
            "document:read", "document:write",
            "ocr:run",
            "extraction:read",
            "evidence:read",
            "quesito:read",
            "ai:query",
        ],
    },
    {
        "name": "revisor",
        "description": "Revisor — leitura completa e validação de extrações e provas",
        "permissions": [
            "case:read",
            "document:read",
            "extraction:read", "extraction:validate",
            "evidence:read", "evidence:validate",
            "quesito:read", "quesito:review",
            "ai:query", "ai:review",
            "audit:read",
        ],
    },
    {
        "name": "leitura",
        "description": "Acesso somente leitura ao processo",
        "permissions": [
            "case:read",
            "document:read",
            "extraction:read",
            "evidence:read",
            "quesito:read",
        ],
    },
]
