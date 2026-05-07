"""Add question_evidence_links table."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0022_question_evidence_links"
down_revision = "0021_quesitos_tema_tipo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create question_evidence_links table."""
    op.create_table(
        "question_evidence_links",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("quesito_id", sa.String(36), nullable=False),
        sa.Column("evidence_item_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["quesito_id"], ["quesitos.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_item_id"], ["evidence_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_question_evidence_links_quesito_id"),
        "question_evidence_links",
        ["quesito_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_evidence_links_evidence_item_id"),
        "question_evidence_links",
        ["evidence_item_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop question_evidence_links table."""
    op.drop_index(
        op.f("ix_question_evidence_links_evidence_item_id"),
        table_name="question_evidence_links",
    )
    op.drop_index(
        op.f("ix_question_evidence_links_quesito_id"),
        table_name="question_evidence_links",
    )
    op.drop_table("question_evidence_links")
