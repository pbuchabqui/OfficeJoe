"""Add OCR confidence markers to file_pages.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-06 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("file_pages", sa.Column("average_confidence", sa.Float(), nullable=True))
    op.add_column(
        "file_pages",
        sa.Column("low_confidence", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_file_pages_low_confidence", "file_pages", ["low_confidence"])


def downgrade() -> None:
    op.drop_index("ix_file_pages_low_confidence", table_name="file_pages")
    op.drop_column("file_pages", "low_confidence")
    op.drop_column("file_pages", "average_confidence")
