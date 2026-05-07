"""Create technical_limitations table.

Revision ID: 0020
Revises: 0019
Create Date: 2024-05-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "technical_limitations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("technical_impact", sa.Text(), nullable=False),
        sa.Column("criticality", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("diligence_id", sa.String(36), nullable=True),
        sa.Column("quesito_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["diligence_id"], ["diligences.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quesito_id"], ["quesitos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_technical_limitations_case_id"),
        "technical_limitations",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_technical_limitations_criticality"),
        "technical_limitations",
        ["criticality"],
        unique=False,
    )
    op.create_index(
        op.f("ix_technical_limitations_diligence_id"),
        "technical_limitations",
        ["diligence_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_technical_limitations_quesito_id"),
        "technical_limitations",
        ["quesito_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_technical_limitations_quesito_id"),
        table_name="technical_limitations",
    )
    op.drop_index(
        op.f("ix_technical_limitations_diligence_id"),
        table_name="technical_limitations",
    )
    op.drop_index(
        op.f("ix_technical_limitations_criticality"),
        table_name="technical_limitations",
    )
    op.drop_index(
        op.f("ix_technical_limitations_case_id"),
        table_name="technical_limitations",
    )
    op.drop_table("technical_limitations")
