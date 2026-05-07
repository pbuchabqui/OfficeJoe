"""Add evidence validation fields.

Revision ID: 0015
Revises: 0014
Create Date: 2024-05-07 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evidence_items",
        sa.Column("validation_status", sa.String(50), nullable=False, server_default="pending"),
    )
    op.add_column(
        "evidence_items",
        sa.Column("validated_by", sa.String(36), nullable=True),
    )
    op.add_column(
        "evidence_items",
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "evidence_items",
        sa.Column("rejection_reason", sa.String(2000), nullable=True),
    )
    op.create_foreign_key(
        "fk_evidence_items_validated_by_users",
        "evidence_items",
        "users",
        ["validated_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_evidence_items_validated_by_users", "evidence_items", type_="foreignkey"
    )
    op.drop_column("evidence_items", "rejection_reason")
    op.drop_column("evidence_items", "validated_at")
    op.drop_column("evidence_items", "validated_by")
    op.drop_column("evidence_items", "validation_status")
