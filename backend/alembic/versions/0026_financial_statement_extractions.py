"""Add financial statement extraction tables.

Three tables:
  financial_statement_extractions   -- one row per ficha financeira
  financial_statement_competencies  -- competency/month blocks
  financial_statement_rubrics       -- rubrics/values per competency
"""
import sqlalchemy as sa
from alembic import op

revision = "0026_financial_statement_extractions"
down_revision = "0025_timecard_extractions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # financial_statement_extractions
    # ------------------------------------------------------------------
    op.create_table(
        "financial_statement_extractions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("evidence_item_id", sa.String(36), nullable=True),
        sa.Column("page_start", sa.Integer, nullable=False),
        sa.Column("page_end", sa.Integer, nullable=False),
        sa.Column(
            "periodo_inicio",
            sa.String(7),
            nullable=True,
            comment="Initial competency in MM/YYYY format when identifiable.",
        ),
        sa.Column(
            "periodo_fim",
            sa.String(7),
            nullable=True,
            comment="Final competency in MM/YYYY format when identifiable.",
        ),
        sa.Column("layout_variant", sa.String(50), nullable=False, server_default="generico"),
        sa.Column("layout_confidence", sa.Float, nullable=True),
        sa.Column("layout_metadata", sa.JSON, nullable=True),
        sa.Column("extraction_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("reviewed_by_id", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_item_id"], ["evidence_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_financial_statement_extractions_document_id",
        "financial_statement_extractions",
        ["document_id"],
    )
    op.create_index(
        "ix_financial_statement_extractions_case_id",
        "financial_statement_extractions",
        ["case_id"],
    )
    op.create_index(
        "ix_financial_statement_extractions_evidence_item_id",
        "financial_statement_extractions",
        ["evidence_item_id"],
    )
    op.create_index(
        "ix_financial_statement_extractions_extraction_status",
        "financial_statement_extractions",
        ["extraction_status"],
    )

    # ------------------------------------------------------------------
    # financial_statement_competencies
    # ------------------------------------------------------------------
    op.create_table(
        "financial_statement_competencies",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("financial_statement_id", sa.String(36), nullable=False),
        sa.Column("file_page_id", sa.String(36), nullable=True),
        sa.Column(
            "competencia",
            sa.String(7),
            nullable=False,
            comment="Competency in MM/YYYY format.",
        ),
        sa.Column("competencia_raw", sa.String(50), nullable=True),
        sa.Column("section_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("raw_section", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("validation_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("corrected_competencia", sa.String(7), nullable=True),
        sa.Column("correction_note", sa.String(1000), nullable=True),
        sa.Column("validated_by_id", sa.String(36), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["financial_statement_id"],
            ["financial_statement_extractions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["file_page_id"], ["file_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "financial_statement_id",
            "competencia",
            "section_index",
            name="uq_financial_statement_competencies_statement_competencia_section",
        ),
    )
    op.create_index(
        "ix_financial_statement_competencies_financial_statement_id",
        "financial_statement_competencies",
        ["financial_statement_id"],
    )
    op.create_index(
        "ix_financial_statement_competencies_file_page_id",
        "financial_statement_competencies",
        ["file_page_id"],
    )
    op.create_index(
        "ix_financial_statement_competencies_competencia",
        "financial_statement_competencies",
        ["competencia"],
    )
    op.create_index(
        "ix_financial_statement_competencies_validation_status",
        "financial_statement_competencies",
        ["validation_status"],
    )

    # ------------------------------------------------------------------
    # financial_statement_rubrics
    # ------------------------------------------------------------------
    op.create_table(
        "financial_statement_rubrics",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("competency_id", sa.String(36), nullable=False),
        sa.Column("file_page_id", sa.String(36), nullable=True),
        sa.Column("line_index", sa.Integer, nullable=False),
        sa.Column("codigo", sa.String(30), nullable=True),
        sa.Column("descricao", sa.String(250), nullable=False),
        sa.Column("rubric_type", sa.String(20), nullable=False, server_default="outro"),
        sa.Column("referencia_raw", sa.String(100), nullable=True),
        sa.Column("referencia_normalized", sa.String(100), nullable=True),
        sa.Column("valor_raw", sa.String(100), nullable=True),
        sa.Column("valor_decimal", sa.Float, nullable=True),
        sa.Column("raw_row", sa.String(1000), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("validation_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("corrected_referencia", sa.String(100), nullable=True),
        sa.Column("corrected_valor", sa.String(100), nullable=True),
        sa.Column("corrected_rubric_type", sa.String(20), nullable=True),
        sa.Column("correction_note", sa.String(1000), nullable=True),
        sa.Column("validated_by_id", sa.String(36), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["competency_id"],
            ["financial_statement_competencies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["file_page_id"], ["file_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "competency_id",
            "line_index",
            name="uq_financial_statement_rubrics_competency_line",
        ),
    )
    op.create_index(
        "ix_financial_statement_rubrics_competency_id",
        "financial_statement_rubrics",
        ["competency_id"],
    )
    op.create_index(
        "ix_financial_statement_rubrics_file_page_id",
        "financial_statement_rubrics",
        ["file_page_id"],
    )
    op.create_index(
        "ix_financial_statement_rubrics_codigo",
        "financial_statement_rubrics",
        ["codigo"],
    )
    op.create_index(
        "ix_financial_statement_rubrics_rubric_type",
        "financial_statement_rubrics",
        ["rubric_type"],
    )
    op.create_index(
        "ix_financial_statement_rubrics_validation_status",
        "financial_statement_rubrics",
        ["validation_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_financial_statement_rubrics_validation_status", table_name="financial_statement_rubrics")
    op.drop_index("ix_financial_statement_rubrics_rubric_type", table_name="financial_statement_rubrics")
    op.drop_index("ix_financial_statement_rubrics_codigo", table_name="financial_statement_rubrics")
    op.drop_index("ix_financial_statement_rubrics_file_page_id", table_name="financial_statement_rubrics")
    op.drop_index("ix_financial_statement_rubrics_competency_id", table_name="financial_statement_rubrics")
    op.drop_table("financial_statement_rubrics")

    op.drop_index(
        "ix_financial_statement_competencies_validation_status",
        table_name="financial_statement_competencies",
    )
    op.drop_index(
        "ix_financial_statement_competencies_competencia",
        table_name="financial_statement_competencies",
    )
    op.drop_index(
        "ix_financial_statement_competencies_file_page_id",
        table_name="financial_statement_competencies",
    )
    op.drop_index(
        "ix_financial_statement_competencies_financial_statement_id",
        table_name="financial_statement_competencies",
    )
    op.drop_table("financial_statement_competencies")

    op.drop_index(
        "ix_financial_statement_extractions_extraction_status",
        table_name="financial_statement_extractions",
    )
    op.drop_index(
        "ix_financial_statement_extractions_evidence_item_id",
        table_name="financial_statement_extractions",
    )
    op.drop_index("ix_financial_statement_extractions_case_id", table_name="financial_statement_extractions")
    op.drop_index("ix_financial_statement_extractions_document_id", table_name="financial_statement_extractions")
    op.drop_table("financial_statement_extractions")
