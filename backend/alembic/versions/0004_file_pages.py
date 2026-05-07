"""Add file_pages table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-06 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "file_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "file_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("status_ocr", sa.String(50), nullable=False),
        sa.Column("status_preview", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("file_id", "page_number", name="uq_file_pages_file_page_number"),
    )
    op.create_index("ix_file_pages_file_id", "file_pages", ["file_id"])


def downgrade() -> None:
    op.drop_index("ix_file_pages_file_id", table_name="file_pages")
    op.drop_table("file_pages")
