"""Add calculation control tables."""
import sqlalchemy as sa
from alembic import op

revision = "0028_calculations"
down_revision = "0027_document_contradictions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calculations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("calculation_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("responsible_user_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="rascunho"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calculations_case_id", "calculations", ["case_id"])
    op.create_index("ix_calculations_calculation_type", "calculations", ["calculation_type"])
    op.create_index("ix_calculations_responsible_user_id", "calculations", ["responsible_user_id"])
    op.create_index("ix_calculations_status", "calculations", ["status"])

    op.create_table(
        "calculation_versions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("calculation_id", sa.String(36), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_bucket", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("premises", sa.Text, nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
        sa.Column("created_by_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["calculation_id"], ["calculations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint(
            "calculation_id",
            "version_number",
            name="uq_calculation_versions_calculation_version",
        ),
    )
    op.create_index("ix_calculation_versions_calculation_id", "calculation_versions", ["calculation_id"])
    op.create_index("ix_calculation_versions_sha256_hash", "calculation_versions", ["sha256_hash"])
    op.create_index("ix_calculation_versions_created_by_id", "calculation_versions", ["created_by_id"])


def downgrade() -> None:
    op.drop_index("ix_calculation_versions_created_by_id", table_name="calculation_versions")
    op.drop_index("ix_calculation_versions_sha256_hash", table_name="calculation_versions")
    op.drop_index("ix_calculation_versions_calculation_id", table_name="calculation_versions")
    op.drop_table("calculation_versions")

    op.drop_index("ix_calculations_status", table_name="calculations")
    op.drop_index("ix_calculations_responsible_user_id", table_name="calculations")
    op.drop_index("ix_calculations_calculation_type", table_name="calculations")
    op.drop_index("ix_calculations_case_id", table_name="calculations")
    op.drop_table("calculations")
