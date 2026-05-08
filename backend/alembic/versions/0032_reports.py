"""Add reports and report sections tables."""
import sqlalchemy as sa
from alembic import op

revision = "0032_reports"
down_revision = "0031_tech_diary_evid_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="rascunho"),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_case_id", "reports", ["case_id"])
    op.create_index("ix_reports_report_type", "reports", ["report_type"])
    op.create_index("ix_reports_status", "reports", ["status"])

    op.create_table(
        "report_sections",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("report_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("section_order", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("review_status", sa.String(50), nullable=False, server_default="pendente"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "section_order", name="uq_report_sections_report_order"),
    )
    op.create_index("ix_report_sections_report_id", "report_sections", ["report_id"])
    op.create_index("ix_report_sections_review_status", "report_sections", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_report_sections_review_status", table_name="report_sections")
    op.drop_index("ix_report_sections_report_id", table_name="report_sections")
    op.drop_table("report_sections")

    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_report_type", table_name="reports")
    op.drop_index("ix_reports_case_id", table_name="reports")
    op.drop_table("reports")
