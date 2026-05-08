"""Add AI draft tracking fields to report sections."""
import sqlalchemy as sa
from alembic import op

revision = "0034_rpt_ai_draft_fields"
down_revision = "0033_rpt_evid_matrix_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_sections",
        sa.Column("is_ai_generated", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column("report_sections", sa.Column("ai_provider", sa.String(50), nullable=True))
    op.add_column("report_sections", sa.Column("ai_model", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("report_sections", "ai_model")
    op.drop_column("report_sections", "ai_provider")
    op.drop_column("report_sections", "is_ai_generated")
