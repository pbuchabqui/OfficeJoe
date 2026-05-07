"""Add document contradictions table."""
import sqlalchemy as sa
from alembic import op

revision = "0027_document_contradictions"
down_revision = "0026_financial_statement_extractions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_contradictions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("competencia", sa.String(7), nullable=False),
        sa.Column("rule_key", sa.String(100), nullable=False),
        sa.Column("holerite_extraction_id", sa.String(36), nullable=False),
        sa.Column("holerite_verba_id", sa.String(36), nullable=False),
        sa.Column("financial_statement_id", sa.String(36), nullable=False),
        sa.Column("financial_statement_rubric_id", sa.String(36), nullable=False),
        sa.Column("rubric_key", sa.String(300), nullable=False),
        sa.Column("rubric_code", sa.String(30), nullable=True),
        sa.Column("rubric_description", sa.String(300), nullable=False),
        sa.Column("holerite_value_raw", sa.String(100), nullable=True),
        sa.Column("holerite_value_decimal", sa.Float, nullable=True),
        sa.Column("financial_value_raw", sa.String(100), nullable=True),
        sa.Column("financial_value_decimal", sa.Float, nullable=True),
        sa.Column("delta_value", sa.Float, nullable=True),
        sa.Column("compared_values", sa.JSON, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["holerite_extraction_id"],
            ["holerite_extractions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["holerite_verba_id"], ["holerite_verbas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_statement_id"],
            ["financial_statement_extractions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["financial_statement_rubric_id"],
            ["financial_statement_rubrics.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_contradictions_case_id", "document_contradictions", ["case_id"])
    op.create_index("ix_document_contradictions_competencia", "document_contradictions", ["competencia"])
    op.create_index("ix_document_contradictions_rule_key", "document_contradictions", ["rule_key"])
    op.create_index(
        "ix_document_contradictions_holerite_extraction_id",
        "document_contradictions",
        ["holerite_extraction_id"],
    )
    op.create_index(
        "ix_document_contradictions_holerite_verba_id",
        "document_contradictions",
        ["holerite_verba_id"],
    )
    op.create_index(
        "ix_document_contradictions_financial_statement_id",
        "document_contradictions",
        ["financial_statement_id"],
    )
    op.create_index(
        "ix_document_contradictions_financial_statement_rubric_id",
        "document_contradictions",
        ["financial_statement_rubric_id"],
    )
    op.create_index("ix_document_contradictions_rubric_key", "document_contradictions", ["rubric_key"])
    op.create_index("ix_document_contradictions_status", "document_contradictions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_document_contradictions_status", table_name="document_contradictions")
    op.drop_index("ix_document_contradictions_rubric_key", table_name="document_contradictions")
    op.drop_index(
        "ix_document_contradictions_financial_statement_rubric_id",
        table_name="document_contradictions",
    )
    op.drop_index("ix_document_contradictions_financial_statement_id", table_name="document_contradictions")
    op.drop_index("ix_document_contradictions_holerite_verba_id", table_name="document_contradictions")
    op.drop_index("ix_document_contradictions_holerite_extraction_id", table_name="document_contradictions")
    op.drop_index("ix_document_contradictions_rule_key", table_name="document_contradictions")
    op.drop_index("ix_document_contradictions_competencia", table_name="document_contradictions")
    op.drop_index("ix_document_contradictions_case_id", table_name="document_contradictions")
    op.drop_table("document_contradictions")
