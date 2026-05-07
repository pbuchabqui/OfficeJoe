"""Add human validation fields to page_classifications.

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-07 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "page_classifications",
        sa.Column("human_validated", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "page_classifications",
        sa.Column(
            "validated_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "page_classifications",
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("page_classifications", "validated_at")
    op.drop_column("page_classifications", "validated_by")
    op.drop_column("page_classifications", "human_validated")
