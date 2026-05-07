"""Create evidence_items table.

Revision ID: 0014
Revises: 0013
Create Date: 2024-05-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text_excerpt", sa.String(4000), nullable=False),
        sa.Column("coordinates", sa.JSON(), nullable=True),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("notes", sa.String(2000), nullable=False),
        sa.Column("reliability_level", sa.Integer(), nullable=False),
        sa.Column("validated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_items_case_id"), "evidence_items", ["case_id"], unique=False
    )
    op.create_index(
        op.f("ix_evidence_items_document_id"), "evidence_items", ["document_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_evidence_items_document_id"), table_name="evidence_items")
    op.drop_index(op.f("ix_evidence_items_case_id"), table_name="evidence_items")
    op.drop_table("evidence_items")
