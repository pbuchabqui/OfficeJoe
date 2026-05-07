"""Add technical diary evidence links table."""
import sqlalchemy as sa
from alembic import op

revision = "0031_technical_diary_evidence_links"
down_revision = "0030_technical_diary_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "technical_diary_evidence_links",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("technical_diary_entry_id", sa.String(36), nullable=False),
        sa.Column("evidence_item_id", sa.String(36), nullable=False),
        sa.Column("linked_by_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["technical_diary_entry_id"],
            ["technical_diary_entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["evidence_item_id"], ["evidence_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "technical_diary_entry_id",
            "evidence_item_id",
            name="uq_technical_diary_evidence_links_entry_evidence",
        ),
    )
    op.create_index(
        "ix_technical_diary_evidence_links_technical_diary_entry_id",
        "technical_diary_evidence_links",
        ["technical_diary_entry_id"],
    )
    op.create_index(
        "ix_technical_diary_evidence_links_evidence_item_id",
        "technical_diary_evidence_links",
        ["evidence_item_id"],
    )
    op.create_index(
        "ix_technical_diary_evidence_links_linked_by_id",
        "technical_diary_evidence_links",
        ["linked_by_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_technical_diary_evidence_links_linked_by_id", table_name="technical_diary_evidence_links")
    op.drop_index("ix_technical_diary_evidence_links_evidence_item_id", table_name="technical_diary_evidence_links")
    op.drop_index(
        "ix_technical_diary_evidence_links_technical_diary_entry_id",
        table_name="technical_diary_evidence_links",
    )
    op.drop_table("technical_diary_evidence_links")
