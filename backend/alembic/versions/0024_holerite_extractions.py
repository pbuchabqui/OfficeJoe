"""Add holerite extraction tables.

Three tables:
  holerite_extractions  — one row per payslip found in a document
  holerite_fields       — header/total fields with per-field validation status
  holerite_verbas       — earnings/deduction line items with per-line validation status
"""
import sqlalchemy as sa
from alembic import op

revision = "0024_holerite_extractions"
down_revision = "0023_question_draft_answers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # holerite_extractions
    # ------------------------------------------------------------------
    op.create_table(
        "holerite_extractions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("evidence_item_id", sa.String(36), nullable=True),
        sa.Column("page_start", sa.Integer, nullable=False),
        sa.Column("page_end", sa.Integer, nullable=False),
        sa.Column("competencia", sa.String(7), nullable=True),
        sa.Column("layout_variant", sa.String(50), nullable=False, server_default="generico"),
        sa.Column("layout_confidence", sa.Float, nullable=True),
        sa.Column("layout_metadata", sa.JSON, nullable=True),
        sa.Column("extraction_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("math_check_passed", sa.Boolean, nullable=True),
        sa.Column("math_check_delta", sa.String(50), nullable=True),
        sa.Column("math_check_notes", sa.Text, nullable=True),
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
    op.create_index("ix_holerite_extractions_document_id", "holerite_extractions", ["document_id"])
    op.create_index("ix_holerite_extractions_case_id", "holerite_extractions", ["case_id"])
    op.create_index("ix_holerite_extractions_evidence_item_id", "holerite_extractions", ["evidence_item_id"])
    op.create_index("ix_holerite_extractions_competencia", "holerite_extractions", ["competencia"])
    op.create_index("ix_holerite_extractions_extraction_status", "holerite_extractions", ["extraction_status"])

    # ------------------------------------------------------------------
    # holerite_fields
    # ------------------------------------------------------------------
    op.create_table(
        "holerite_fields",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("holerite_id", sa.String(36), nullable=False),
        sa.Column("file_page_id", sa.String(36), nullable=True),
        sa.Column("field_type", sa.String(50), nullable=False),
        sa.Column("raw_value", sa.String(500), nullable=True),
        sa.Column("normalized_value", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("validation_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("corrected_value", sa.String(500), nullable=True),
        sa.Column("correction_note", sa.String(1000), nullable=True),
        sa.Column("validated_by_id", sa.String(36), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["holerite_id"], ["holerite_extractions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_page_id"], ["file_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("holerite_id", "field_type", name="uq_holerite_fields_holerite_type"),
    )
    op.create_index("ix_holerite_fields_holerite_id", "holerite_fields", ["holerite_id"])
    op.create_index("ix_holerite_fields_field_type", "holerite_fields", ["field_type"])
    op.create_index("ix_holerite_fields_validation_status", "holerite_fields", ["validation_status"])

    # ------------------------------------------------------------------
    # holerite_verbas
    # ------------------------------------------------------------------
    op.create_table(
        "holerite_verbas",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("holerite_id", sa.String(36), nullable=False),
        sa.Column("file_page_id", sa.String(36), nullable=True),
        sa.Column("line_index", sa.Integer, nullable=False),
        sa.Column("codigo", sa.String(20), nullable=True),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("referencia", sa.String(50), nullable=True),
        sa.Column("valor_raw", sa.String(50), nullable=True),
        sa.Column("valor_decimal", sa.Float, nullable=True),
        sa.Column("tipo", sa.String(15), nullable=False, server_default="informativo"),
        sa.Column("raw_row", sa.String(500), nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("validation_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("corrected_valor", sa.String(50), nullable=True),
        sa.Column("corrected_tipo", sa.String(15), nullable=True),
        sa.Column("correction_note", sa.String(500), nullable=True),
        sa.Column("validated_by_id", sa.String(36), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["holerite_id"], ["holerite_extractions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_page_id"], ["file_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_holerite_verbas_holerite_id", "holerite_verbas", ["holerite_id"])
    op.create_index("ix_holerite_verbas_validation_status", "holerite_verbas", ["validation_status"])


def downgrade() -> None:
    op.drop_index("ix_holerite_verbas_validation_status", table_name="holerite_verbas")
    op.drop_index("ix_holerite_verbas_holerite_id", table_name="holerite_verbas")
    op.drop_table("holerite_verbas")

    op.drop_index("ix_holerite_fields_validation_status", table_name="holerite_fields")
    op.drop_index("ix_holerite_fields_field_type", table_name="holerite_fields")
    op.drop_index("ix_holerite_fields_holerite_id", table_name="holerite_fields")
    op.drop_table("holerite_fields")

    op.drop_index("ix_holerite_extractions_extraction_status", table_name="holerite_extractions")
    op.drop_index("ix_holerite_extractions_competencia", table_name="holerite_extractions")
    op.drop_index("ix_holerite_extractions_evidence_item_id", table_name="holerite_extractions")
    op.drop_index("ix_holerite_extractions_case_id", table_name="holerite_extractions")
    op.drop_index("ix_holerite_extractions_document_id", table_name="holerite_extractions")
    op.drop_table("holerite_extractions")
