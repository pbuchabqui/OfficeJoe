"""Add technical diary entries table."""
import sqlalchemy as sa
from alembic import op

revision = "0030_technical_diary_entries"
down_revision = "0029_calculation_evidence_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "technical_diary_entries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("responsible_user_id", sa.String(36), nullable=True),
        sa.Column("decision_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("technical_justification", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_technical_diary_entries_case_id", "technical_diary_entries", ["case_id"])
    op.create_index("ix_technical_diary_entries_entry_date", "technical_diary_entries", ["entry_date"])
    op.create_index(
        "ix_technical_diary_entries_responsible_user_id",
        "technical_diary_entries",
        ["responsible_user_id"],
    )
    op.create_index(
        "ix_technical_diary_entries_decision_type",
        "technical_diary_entries",
        ["decision_type"],
    )
    op.create_index("ix_technical_diary_entries_status", "technical_diary_entries", ["status"])


def downgrade() -> None:
    op.drop_index("ix_technical_diary_entries_status", table_name="technical_diary_entries")
    op.drop_index("ix_technical_diary_entries_decision_type", table_name="technical_diary_entries")
    op.drop_index("ix_technical_diary_entries_responsible_user_id", table_name="technical_diary_entries")
    op.drop_index("ix_technical_diary_entries_entry_date", table_name="technical_diary_entries")
    op.drop_index("ix_technical_diary_entries_case_id", table_name="technical_diary_entries")
    op.drop_table("technical_diary_entries")
