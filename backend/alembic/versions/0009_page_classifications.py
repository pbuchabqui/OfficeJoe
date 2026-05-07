"""Add page_classifications table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-07 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "page_classifications",
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
        sa.Column("document_class", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("file_page_id", name="uq_page_classifications_file_page_id"),
    )
    op.create_index("ix_page_classifications_file_page_id", "page_classifications", ["file_page_id"])
    op.create_index("ix_page_classifications_file_id", "page_classifications", ["file_id"])
    op.create_index("ix_page_classifications_page_number", "page_classifications", ["page_number"])
    op.create_index("ix_page_classifications_document_class", "page_classifications", ["document_class"])


def downgrade() -> None:
    op.drop_index("ix_page_classifications_document_class", table_name="page_classifications")
    op.drop_index("ix_page_classifications_page_number", table_name="page_classifications")
    op.drop_index("ix_page_classifications_file_id", table_name="page_classifications")
    op.drop_index("ix_page_classifications_file_page_id", table_name="page_classifications")
    op.drop_table("page_classifications")
