"""Create diligences table.

Revision ID: 0017
Revises: 0016
Create Date: 2024-05-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diligences",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("number", sa.String(100), nullable=False),
        sa.Column("recipient", sa.String(500), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("observations", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
    )
    op.create_index(
        op.f("ix_diligences_case_id"),
        "diligences",
        ["case_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_diligences_case_id"), table_name="diligences"
    )
    op.drop_table("diligences")
