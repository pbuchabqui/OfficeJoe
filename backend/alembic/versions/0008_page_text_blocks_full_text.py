"""Add PostgreSQL full-text index for OCR blocks.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-06 00:00:00
"""
from __future__ import annotations

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX ix_page_text_blocks_text_fts
        ON page_text_blocks
        USING GIN (to_tsvector('portuguese', coalesce(text, '')))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_page_text_blocks_text_fts")
