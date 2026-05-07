"""Add report attachments table."""
import sqlalchemy as sa
from alembic import op

revision = "0036_report_attachments"
down_revision = "0035_report_checklist_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_attachments",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("report_id", sa.String(36), nullable=False),
        sa.Column("attachment_type", sa.String(20), nullable=False),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("file_id", sa.String(36), nullable=True),
        sa.Column("calculation_version_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["calculation_version_id"],
            ["calculation_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_id",
            "attachment_type",
            "number",
            name="uq_report_attachments_report_type_number",
        ),
    )
    op.create_index("ix_report_attachments_report_id", "report_attachments", ["report_id"])
    op.create_index(
        "ix_report_attachments_attachment_type",
        "report_attachments",
        ["attachment_type"],
    )
    op.create_index("ix_report_attachments_file_id", "report_attachments", ["file_id"])
    op.create_index(
        "ix_report_attachments_calculation_version_id",
        "report_attachments",
        ["calculation_version_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_attachments_calculation_version_id",
        table_name="report_attachments",
    )
    op.drop_index("ix_report_attachments_file_id", table_name="report_attachments")
    op.drop_index("ix_report_attachments_attachment_type", table_name="report_attachments")
    op.drop_index("ix_report_attachments_report_id", table_name="report_attachments")
    op.drop_table("report_attachments")
