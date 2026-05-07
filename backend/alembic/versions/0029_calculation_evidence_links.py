"""Add calculation evidence links table."""
import sqlalchemy as sa
from alembic import op

revision = "0029_calculation_evidence_links"
down_revision = "0028_calculations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calculation_evidence_links",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("calculation_version_id", sa.String(36), nullable=False),
        sa.Column("evidence_item_id", sa.String(36), nullable=False),
        sa.Column("linked_by_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["calculation_version_id"],
            ["calculation_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["evidence_item_id"], ["evidence_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "calculation_version_id",
            "evidence_item_id",
            name="uq_calculation_evidence_links_version_evidence",
        ),
    )
    op.create_index(
        "ix_calculation_evidence_links_calculation_version_id",
        "calculation_evidence_links",
        ["calculation_version_id"],
    )
    op.create_index(
        "ix_calculation_evidence_links_evidence_item_id",
        "calculation_evidence_links",
        ["evidence_item_id"],
    )
    op.create_index(
        "ix_calculation_evidence_links_linked_by_id",
        "calculation_evidence_links",
        ["linked_by_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_calculation_evidence_links_linked_by_id", table_name="calculation_evidence_links")
    op.drop_index("ix_calculation_evidence_links_evidence_item_id", table_name="calculation_evidence_links")
    op.drop_index(
        "ix_calculation_evidence_links_calculation_version_id",
        table_name="calculation_evidence_links",
    )
    op.drop_table("calculation_evidence_links")
