"""Add inventory item editing fields

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_inventory_items",
        sa.Column("custom_label", sa.String(255), nullable=True),
    )
    op.add_column(
        "document_inventory_items",
        sa.Column("is_relevant", sa.Boolean, nullable=False, server_default="1"),
    )
    op.add_column(
        "document_inventory_items",
        sa.Column(
            "edited_by_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "document_inventory_items",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_document_inventory_items_edited_by_id",
        "document_inventory_items",
        ["edited_by_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_inventory_items_edited_by_id", "document_inventory_items"
    )
    op.drop_column("document_inventory_items", "edited_at")
    op.drop_column("document_inventory_items", "edited_by_id")
    op.drop_column("document_inventory_items", "is_relevant")
    op.drop_column("document_inventory_items", "custom_label")
