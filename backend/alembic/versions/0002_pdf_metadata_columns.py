"""Add initial PDF metadata columns to documents.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-06 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("pdf_is_valid", sa.Boolean(), nullable=True))
    op.add_column("documents", sa.Column("has_native_text", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "has_native_text")
    op.drop_column("documents", "pdf_is_valid")
