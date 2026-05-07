"""Add document reception fields to diligence_items.

Revision ID: 0019
Revises: 0018
Create Date: 2024-05-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "diligence_items",
        sa.Column("documento_recebido_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "diligence_items",
        sa.Column("status_recebimento", sa.String(50), nullable=False, server_default="pendente"),
    )
    op.add_column(
        "diligence_items",
        sa.Column("observacao_pendencia", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_diligence_items_documento_recebido_id",
        "diligence_items",
        "documents",
        ["documento_recebido_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_diligence_items_documento_recebido_id"),
        "diligence_items",
        ["documento_recebido_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_diligence_items_documento_recebido_id"), table_name="diligence_items"
    )
    op.drop_constraint(
        "fk_diligence_items_documento_recebido_id", "diligence_items", type_="foreignkey"
    )
    op.drop_column("diligence_items", "observacao_pendencia")
    op.drop_column("diligence_items", "status_recebimento")
    op.drop_column("diligence_items", "documento_recebido_id")
