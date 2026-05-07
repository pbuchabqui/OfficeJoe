"""Add question_draft_answers table."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0023_question_draft_answers"
down_revision = "0022_question_evidence_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create question_draft_answers table."""
    op.create_table(
        "question_draft_answers",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("quesito_id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("draft_text", sa.Text, nullable=False),
        sa.Column("ai_model", sa.String(100), nullable=False, server_default="mock-v1"),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("evidence_ids_used", sa.JSON, nullable=True),
        sa.Column("generated_by_id", sa.String(36), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("is_reviewed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["quesito_id"], ["quesitos.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["generated_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_question_draft_answers_quesito_id"),
        "question_draft_answers",
        ["quesito_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_draft_answers_case_id"),
        "question_draft_answers",
        ["case_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop question_draft_answers table."""
    op.drop_index(
        op.f("ix_question_draft_answers_case_id"),
        table_name="question_draft_answers",
    )
    op.drop_index(
        op.f("ix_question_draft_answers_quesito_id"),
        table_name="question_draft_answers",
    )
    op.drop_table("question_draft_answers")
