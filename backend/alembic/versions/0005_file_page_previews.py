"""Add preview storage key to file_pages.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-06 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("file_pages", sa.Column("preview_storage_key", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("file_pages", "preview_storage_key")
