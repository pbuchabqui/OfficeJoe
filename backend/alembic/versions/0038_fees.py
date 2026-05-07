"""Add fees table."""
import sqlalchemy as sa
from alembic import op

revision = "0038_fees"
down_revision = "0037_report_clarifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fees",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("proposed_amount", sa.Float, nullable=True),
        sa.Column("arbitrated_amount", sa.Float, nullable=True),
        sa.Column("deposited_amount", sa.Float, nullable=True),
        sa.Column("withdrawn_amount", sa.Float, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="proposto"),
        sa.Column("proposed_at", sa.Date, nullable=True),
        sa.Column("arbitrated_at", sa.Date, nullable=True),
        sa.Column("deposited_at", sa.Date, nullable=True),
        sa.Column("withdrawn_at", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fees_case_id", "fees", ["case_id"])
    op.create_index("ix_fees_status", "fees", ["status"])


def downgrade() -> None:
    op.drop_index("ix_fees_status", table_name="fees")
    op.drop_index("ix_fees_case_id", table_name="fees")
    op.drop_table("fees")
