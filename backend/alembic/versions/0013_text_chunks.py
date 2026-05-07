"""text_chunks table for semantic search with pgvector

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar extensão pgvector se não existir
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "text_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("page_number", sa.Integer, nullable=False, index=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", sa.String(10000), nullable=False),  # JSON-serialized vector
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Índice para busca semântica (produto interno negado para similaridade)
    op.execute(
        "CREATE INDEX ix_text_chunks_embedding ON text_chunks USING ivfflat (embedding vector_ip_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_index("ix_text_chunks_embedding", "text_chunks")
    op.drop_table("text_chunks")
