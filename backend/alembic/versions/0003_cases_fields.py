"""Campos adicionais de processos e tabela case_parties

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-07 00:00:00

Escopo:
  - Adiciona colunas ausentes na tabela cases:
      tribunal, vara, fase_processual, objeto_pericia,
      data_ciencia, notes, deleted_at
  - Renomeia description → notes (description fica como alias retrocompat.)
  - Cria tabela case_parties
  - Adiciona índices de suporte a filtros frequentes
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── Novas colunas em cases ────────────────────────────────────────────────
    op.add_column("cases", sa.Column("tribunal", sa.String(255), nullable=True))
    op.add_column("cases", sa.Column("vara", sa.String(255), nullable=True))
    op.add_column("cases", sa.Column("fase_processual", sa.String(30), nullable=True))
    op.add_column("cases", sa.Column("objeto_pericia", sa.Text(), nullable=True))
    op.add_column("cases", sa.Column("data_ciencia", sa.String(20), nullable=True))
    op.add_column("cases", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("cases", sa.Column("deleted_at", sa.String(50), nullable=True))

    # Migra dados existentes de description → notes e mantém description
    op.execute("UPDATE cases SET notes = description WHERE notes IS NULL AND description IS NOT NULL")

    # Índices para filtros frequentes
    op.create_index("ix_cases_fase_processual", "cases", ["fase_processual"])
    op.create_index("ix_cases_deleted_at", "cases", ["deleted_at"])

    # ── Tabela case_parties ───────────────────────────────────────────────────
    op.create_table(
        "case_parties",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("cpf_cnpj", sa.String(20), nullable=True),
        sa.Column("lawyer_name", sa.String(255), nullable=True),
        sa.Column("lawyer_oab", sa.String(30), nullable=True),
    )
    op.create_index("ix_case_parties_case_id", "case_parties", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_case_parties_case_id", table_name="case_parties")
    op.drop_table("case_parties")

    op.drop_index("ix_cases_deleted_at", table_name="cases")
    op.drop_index("ix_cases_fase_processual", table_name="cases")

    op.drop_column("cases", "deleted_at")
    op.drop_column("cases", "notes")
    op.drop_column("cases", "data_ciencia")
    op.drop_column("cases", "objeto_pericia")
    op.drop_column("cases", "fase_processual")
    op.drop_column("cases", "vara")
    op.drop_column("cases", "tribunal")
