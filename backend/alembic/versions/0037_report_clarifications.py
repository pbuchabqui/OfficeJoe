"""Add report clarifications table."""
import sqlalchemy as sa
from alembic import op

revision = "0037_report_clarifications"
down_revision = "0036_report_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_clarifications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("report_id", sa.String(36), nullable=False),
        sa.Column("report_version", sa.Integer, nullable=False),
        sa.Column("request_text", sa.Text, nullable=False),
        sa.Column("theme", sa.String(200), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="recebido"),
        sa.Column("preliminary_response", sa.Text, nullable=True),
        sa.Column("final_response", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_clarifications_case_id", "report_clarifications", ["case_id"])
    op.create_index("ix_report_clarifications_report_id", "report_clarifications", ["report_id"])
    op.create_index("ix_report_clarifications_theme", "report_clarifications", ["theme"])
    op.create_index("ix_report_clarifications_status", "report_clarifications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_report_clarifications_status", table_name="report_clarifications")
    op.drop_index("ix_report_clarifications_theme", table_name="report_clarifications")
    op.drop_index("ix_report_clarifications_report_id", table_name="report_clarifications")
    op.drop_index("ix_report_clarifications_case_id", table_name="report_clarifications")
    op.drop_table("report_clarifications")
