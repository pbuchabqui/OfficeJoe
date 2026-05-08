"""Add report section evidence matrix links table."""
import sqlalchemy as sa
from alembic import op

revision = "0033_rpt_evid_matrix_links"
down_revision = "0032_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_section_evidence_matrix_links",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("report_section_id", sa.String(36), nullable=False),
        sa.Column("evidence_matrix_item_id", sa.String(36), nullable=False),
        sa.Column("linked_by_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_section_id"], ["report_sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["evidence_matrix_item_id"],
            ["evidence_matrix_items.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["linked_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_section_id",
            "evidence_matrix_item_id",
            name="uq_report_section_matrix_links_section_matrix",
        ),
    )
    op.create_index(
        "ix_report_section_evidence_matrix_links_report_section_id",
        "report_section_evidence_matrix_links",
        ["report_section_id"],
    )
    op.create_index(
        "ix_report_section_evidence_matrix_links_evidence_matrix_item_id",
        "report_section_evidence_matrix_links",
        ["evidence_matrix_item_id"],
    )
    op.create_index(
        "ix_report_section_evidence_matrix_links_linked_by_id",
        "report_section_evidence_matrix_links",
        ["linked_by_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_section_evidence_matrix_links_linked_by_id",
        table_name="report_section_evidence_matrix_links",
    )
    op.drop_index(
        "ix_report_section_evidence_matrix_links_evidence_matrix_item_id",
        table_name="report_section_evidence_matrix_links",
    )
    op.drop_index(
        "ix_report_section_evidence_matrix_links_report_section_id",
        table_name="report_section_evidence_matrix_links",
    )
    op.drop_table("report_section_evidence_matrix_links")
