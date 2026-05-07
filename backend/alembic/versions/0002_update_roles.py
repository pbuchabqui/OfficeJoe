"""Atualiza perfis: analista, revisor, leitura (substitui assistente e visualizador)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07 00:00:00

Escopo:
  - Renomeia 'assistente' → 'analista'
  - Renomeia 'visualizador' → 'leitura'
  - Adiciona papel 'revisor'
  - Atualiza permissões de perito para refletir extração e laudo
  - Migra usuários existentes para os novos nomes de perfil
  - Altera default da coluna users.role para 'leitura'
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Permissões consolidadas por papel
_PERITO_PERMS = [
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
]
_ANALISTA_PERMS = [
    "case:read", "case:write",
    "document:read", "document:write",
    "ocr:run",
    "extraction:read",
    "evidence:read",
    "quesito:read",
    "ai:query",
]
_REVISOR_PERMS = [
    "case:read",
    "document:read",
    "extraction:read", "extraction:validate",
    "evidence:read", "evidence:validate",
    "quesito:read", "quesito:review",
    "ai:query", "ai:review",
    "audit:read",
]
_LEITURA_PERMS = [
    "case:read",
    "document:read",
    "extraction:read",
    "evidence:read",
    "quesito:read",
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Inserir os novos papéis antes de migrar usuários (FK constraint)
    conn.execute(
        sa.text(
            "INSERT INTO roles (name, description, permissions, is_active, created_at, updated_at) "
            "VALUES (:name, :desc, :perms::jsonb, true, now(), now()) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        [
            {
                "name": "analista",
                "desc": "Analista do perito — leitura e escrita, sem validação e laudo",
                "perms": str(_ANALISTA_PERMS).replace("'", '"'),
            },
            {
                "name": "revisor",
                "desc": "Revisor — leitura completa e validação de extrações e provas",
                "perms": str(_REVISOR_PERMS).replace("'", '"'),
            },
            {
                "name": "leitura",
                "desc": "Acesso somente leitura ao processo",
                "perms": str(_LEITURA_PERMS).replace("'", '"'),
            },
        ],
    )

    # 2. Migrar usuários com papéis antigos
    conn.execute(
        sa.text("UPDATE users SET role = 'analista' WHERE role = 'assistente'")
    )
    conn.execute(
        sa.text("UPDATE users SET role = 'leitura' WHERE role = 'visualizador'")
    )

    # 3. Remover papéis obsoletos (nenhum usuário deve mais referenciar esses nomes)
    conn.execute(sa.text("DELETE FROM roles WHERE name IN ('assistente', 'visualizador')"))

    # 4. Atualizar permissões do perito para refletir módulos de extração e laudo
    conn.execute(
        sa.text(
            "UPDATE roles SET permissions = :perms::jsonb, updated_at = now() "
            "WHERE name = 'perito'"
        ),
        {"perms": str(_PERITO_PERMS).replace("'", '"')},
    )

    # 5. Ajustar default da coluna role em users
    op.alter_column(
        "users",
        "role",
        server_default="leitura",
        existing_type=sa.String(30),
        existing_nullable=False,
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Reverter default
    op.alter_column(
        "users",
        "role",
        server_default="visualizador",
        existing_type=sa.String(30),
        existing_nullable=False,
    )

    # Recriar papéis antigos
    conn.execute(
        sa.text(
            "INSERT INTO roles (name, description, permissions, is_active, created_at, updated_at) "
            "VALUES (:name, :desc, :perms::jsonb, true, now(), now()) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        [
            {
                "name": "assistente",
                "desc": "Assistente do perito — leitura e escrita, sem validação e laudo",
                "perms": str(_ANALISTA_PERMS).replace("'", '"'),
            },
            {
                "name": "visualizador",
                "desc": "Acesso somente leitura ao processo",
                "perms": str(_LEITURA_PERMS).replace("'", '"'),
            },
        ],
    )

    # Reverter usuários migrados
    conn.execute(
        sa.text("UPDATE users SET role = 'assistente' WHERE role = 'analista'")
    )
    conn.execute(
        sa.text("UPDATE users SET role = 'visualizador' WHERE role = 'leitura'")
    )

    # Remover papéis novos
    conn.execute(
        sa.text("DELETE FROM roles WHERE name IN ('analista', 'revisor', 'leitura')")
    )
