"""Create evidence_matrix_items table.

Revision ID: 0016
Revises: 0015
Create Date: 2024-05-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_matrix_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("disputed_fact", sa.String(1000), nullable=False),
        sa.Column("theme", sa.String(500), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("expert_procedure", sa.String(500), nullable=False),
        sa.Column("methodology_or_criteria", sa.Text(), nullable=False),
        sa.Column("result_found", sa.Text(), nullable=False),
        sa.Column("technical_impact", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_matrix_items_case_id"),
        "evidence_matrix_items",
        ["case_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_evidence_matrix_items_case_id"), table_name="evidence_matrix_items"
    )
    op.drop_table("evidence_matrix_items")
