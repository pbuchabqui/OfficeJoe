"""document_inventory_items table

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_inventory_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("document_class", sa.String(100), nullable=False),
        sa.Column("start_page", sa.Integer, nullable=False),
        sa.Column("end_page", sa.Integer, nullable=False),
        sa.Column("page_count", sa.Integer, nullable=False),
        sa.Column("confidence_avg", sa.Float, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_document_inventory_items_document_id",
        "document_inventory_items",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_inventory_items_document_id", "document_inventory_items")
    op.drop_table("document_inventory_items")
