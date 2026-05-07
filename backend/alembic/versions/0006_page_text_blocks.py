"""Add page_text_blocks table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-06 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "page_text_blocks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "file_page_id",
            sa.String(36),
            sa.ForeignKey("file_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("x0", sa.Float(), nullable=False),
        sa.Column("y0", sa.Float(), nullable=False),
        sa.Column("x1", sa.Float(), nullable=False),
        sa.Column("y1", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_page_text_blocks_file_page_id", "page_text_blocks", ["file_page_id"])
    op.create_index("ix_page_text_blocks_file_id", "page_text_blocks", ["file_id"])
    op.create_index("ix_page_text_blocks_page_number", "page_text_blocks", ["page_number"])


def downgrade() -> None:
    op.drop_index("ix_page_text_blocks_page_number", table_name="page_text_blocks")
    op.drop_index("ix_page_text_blocks_file_id", table_name="page_text_blocks")
    op.drop_index("ix_page_text_blocks_file_page_id", table_name="page_text_blocks")
    op.drop_table("page_text_blocks")
