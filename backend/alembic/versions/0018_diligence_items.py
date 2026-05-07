"""Create diligence_items table.

Revision ID: 0018
Revises: 0017
Create Date: 2024-05-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diligence_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("diligence_id", sa.String(36), nullable=False),
        sa.Column("requested_document", sa.String(500), nullable=False),
        sa.Column("period", sa.String(200), nullable=False),
        sa.Column("technical_justification", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["diligence_id"], ["diligences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_diligence_items_diligence_id"),
        "diligence_items",
        ["diligence_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_diligence_items_diligence_id"), table_name="diligence_items"
    )
    op.drop_table("diligence_items")
