"""Add report checklist items table."""
import sqlalchemy as sa
from alembic import op

revision = "0035_report_checklist_items"
down_revision = "0034_rpt_ai_draft_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_checklist_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("report_id", sa.String(36), nullable=False),
        sa.Column("item_key", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("item_order", sa.Integer, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="incompleto"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("updated_by_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "item_key", name="uq_report_checklist_items_report_key"),
    )
    op.create_index("ix_report_checklist_items_report_id", "report_checklist_items", ["report_id"])
    op.create_index("ix_report_checklist_items_item_key", "report_checklist_items", ["item_key"])
    op.create_index("ix_report_checklist_items_status", "report_checklist_items", ["status"])
    op.create_index("ix_report_checklist_items_updated_by_id", "report_checklist_items", ["updated_by_id"])


def downgrade() -> None:
    op.drop_index("ix_report_checklist_items_updated_by_id", table_name="report_checklist_items")
    op.drop_index("ix_report_checklist_items_status", table_name="report_checklist_items")
    op.drop_index("ix_report_checklist_items_item_key", table_name="report_checklist_items")
    op.drop_index("ix_report_checklist_items_report_id", table_name="report_checklist_items")
    op.drop_table("report_checklist_items")
