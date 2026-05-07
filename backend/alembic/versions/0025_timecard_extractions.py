"""Add timecard extraction tables.

Three tables:
  timecard_extractions  -- one row per timecard found in a document
  timecard_days         -- one row per extracted day
  timecard_day_fields   -- per-day marks/fields with per-field validation
"""
import sqlalchemy as sa
from alembic import op

revision = "0025_timecard_extractions"
down_revision = "0024_holerite_extractions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # timecard_extractions
    # ------------------------------------------------------------------
    op.create_table(
        "timecard_extractions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("evidence_item_id", sa.String(36), nullable=True),
        sa.Column("page_start", sa.Integer, nullable=False),
        sa.Column("page_end", sa.Integer, nullable=False),
        sa.Column("competencia", sa.String(7), nullable=True),
        sa.Column("periodo_inicio", sa.Date, nullable=True),
        sa.Column("periodo_fim", sa.Date, nullable=True),
        sa.Column("layout_variant", sa.String(50), nullable=False, server_default="generico"),
        sa.Column("layout_confidence", sa.Float, nullable=True),
        sa.Column("layout_metadata", sa.JSON, nullable=True),
        sa.Column("extraction_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("unreadable_marks_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "unreadable_notes",
            sa.Text,
            nullable=True,
            comment="General notes about unreadable marks across the extracted timecard.",
        ),
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
    op.create_index("ix_timecard_extractions_document_id", "timecard_extractions", ["document_id"])
    op.create_index("ix_timecard_extractions_case_id", "timecard_extractions", ["case_id"])
    op.create_index("ix_timecard_extractions_evidence_item_id", "timecard_extractions", ["evidence_item_id"])
    op.create_index("ix_timecard_extractions_competencia", "timecard_extractions", ["competencia"])
    op.create_index("ix_timecard_extractions_extraction_status", "timecard_extractions", ["extraction_status"])

    # ------------------------------------------------------------------
    # timecard_days
    # ------------------------------------------------------------------
    op.create_table(
        "timecard_days",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("timecard_id", sa.String(36), nullable=False),
        sa.Column("file_page_id", sa.String(36), nullable=True),
        sa.Column("day_index", sa.Integer, nullable=False),
        sa.Column("work_date", sa.Date, nullable=True),
        sa.Column("day_number", sa.Integer, nullable=True),
        sa.Column("weekday_label", sa.String(20), nullable=True),
        sa.Column("raw_row", sa.String(1000), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("validation_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("unreadable_marks_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "unreadable_notes",
            sa.Text,
            nullable=True,
            comment="Day-level notes for marks that are missing, blurred, cut off, or OCR-corrupted.",
        ),
        sa.Column("corrected_date", sa.Date, nullable=True),
        sa.Column("correction_note", sa.String(1000), nullable=True),
        sa.Column("validated_by_id", sa.String(36), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["timecard_id"], ["timecard_extractions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_page_id"], ["file_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("timecard_id", "day_index", name="uq_timecard_days_timecard_day_index"),
    )
    op.create_index("ix_timecard_days_timecard_id", "timecard_days", ["timecard_id"])
    op.create_index("ix_timecard_days_file_page_id", "timecard_days", ["file_page_id"])
    op.create_index("ix_timecard_days_work_date", "timecard_days", ["work_date"])
    op.create_index("ix_timecard_days_validation_status", "timecard_days", ["validation_status"])

    # ------------------------------------------------------------------
    # timecard_day_fields
    # ------------------------------------------------------------------
    op.create_table(
        "timecard_day_fields",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("day_id", sa.String(36), nullable=False),
        sa.Column("file_page_id", sa.String(36), nullable=True),
        sa.Column("field_type", sa.String(50), nullable=False),
        sa.Column("field_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("raw_value", sa.String(500), nullable=True),
        sa.Column(
            "normalized_value",
            sa.String(50),
            nullable=True,
            comment="Time marks should be normalized as HH:MM when legible.",
        ),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("bbox_x0", sa.Float, nullable=True),
        sa.Column("bbox_y0", sa.Float, nullable=True),
        sa.Column("bbox_x1", sa.Float, nullable=True),
        sa.Column("bbox_y1", sa.Float, nullable=True),
        sa.Column("is_unreadable", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "unreadable_note",
            sa.String(1000),
            nullable=True,
            comment="Specific reason for unreadable mark, e.g. blur, overwritten text, or cut page.",
        ),
        sa.Column("validation_status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("corrected_value", sa.String(500), nullable=True),
        sa.Column("correction_note", sa.String(1000), nullable=True),
        sa.Column("validated_by_id", sa.String(36), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["day_id"], ["timecard_days.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_page_id"], ["file_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("day_id", "field_type", "field_order", name="uq_timecard_day_fields_day_type_order"),
    )
    op.create_index("ix_timecard_day_fields_day_id", "timecard_day_fields", ["day_id"])
    op.create_index("ix_timecard_day_fields_file_page_id", "timecard_day_fields", ["file_page_id"])
    op.create_index("ix_timecard_day_fields_field_type", "timecard_day_fields", ["field_type"])
    op.create_index("ix_timecard_day_fields_validation_status", "timecard_day_fields", ["validation_status"])


def downgrade() -> None:
    op.drop_index("ix_timecard_day_fields_validation_status", table_name="timecard_day_fields")
    op.drop_index("ix_timecard_day_fields_field_type", table_name="timecard_day_fields")
    op.drop_index("ix_timecard_day_fields_file_page_id", table_name="timecard_day_fields")
    op.drop_index("ix_timecard_day_fields_day_id", table_name="timecard_day_fields")
    op.drop_table("timecard_day_fields")

    op.drop_index("ix_timecard_days_validation_status", table_name="timecard_days")
    op.drop_index("ix_timecard_days_work_date", table_name="timecard_days")
    op.drop_index("ix_timecard_days_file_page_id", table_name="timecard_days")
    op.drop_index("ix_timecard_days_timecard_id", table_name="timecard_days")
    op.drop_table("timecard_days")

    op.drop_index("ix_timecard_extractions_extraction_status", table_name="timecard_extractions")
    op.drop_index("ix_timecard_extractions_competencia", table_name="timecard_extractions")
    op.drop_index("ix_timecard_extractions_evidence_item_id", table_name="timecard_extractions")
    op.drop_index("ix_timecard_extractions_case_id", table_name="timecard_extractions")
    op.drop_index("ix_timecard_extractions_document_id", table_name="timecard_extractions")
    op.drop_table("timecard_extractions")
