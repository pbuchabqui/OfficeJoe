"""Initial schema – all tables + pgvector extension

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Habilita pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("otp_secret", sa.String(32), nullable=True),
        sa.Column("otp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.String(50), nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── cases ────────────────────────────────────────────────────────────
    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_number", sa.String(100), nullable=False, unique=True),
        sa.Column("case_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("court", sa.String(255), nullable=True),
        sa.Column("court_district", sa.String(255), nullable=True),
        sa.Column("judge_name", sa.String(255), nullable=True),
        sa.Column("appointment_date", sa.String(20), nullable=True),
        sa.Column("deadline_date", sa.String(20), nullable=True),
        sa.Column("filing_date", sa.String(20), nullable=True),
        sa.Column("honorarium_proposed", sa.Integer(), nullable=True),
        sa.Column("honorarium_approved", sa.Integer(), nullable=True),
        sa.Column("responsible_user_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cases_case_number", "cases", ["case_number"])
    op.create_index("ix_cases_status", "cases", ["status"])

    # ── case_parties ─────────────────────────────────────────────────────
    op.create_table(
        "case_parties",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36),
                  sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("cpf_cnpj", sa.String(20), nullable=True),
        sa.Column("lawyer_name", sa.String(255), nullable=True),
        sa.Column("lawyer_oab", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_case_parties_case_id", "case_parties", ["case_id"])

    # ── documents ────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36),
                  sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("total_pages", sa.Integer(), nullable=True),
        sa.Column("storage_bucket", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("storage_version_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("ocr_engine_used", sa.String(50), nullable=True),
        sa.Column("ocr_avg_confidence", sa.String(10), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("ocr_task_id", sa.String(255), nullable=True),
        sa.Column("embedding_task_id", sa.String(255), nullable=True),
        sa.Column("is_original_preserved", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("uploaded_by_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_index("ix_documents_sha256_hash", "documents", ["sha256_hash"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # ── pages ────────────────────────────────────────────────────────────
    op.create_table(
        "pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("text_length", sa.Integer(), nullable=True),
        sa.Column("ocr_engine", sa.String(50), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("has_text_layer", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_image_only", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("width_pt", sa.Float(), nullable=True),
        sa.Column("height_pt", sa.Float(), nullable=True),
        sa.Column("text_blocks", postgresql.JSONB(), nullable=True),
        sa.Column("tables_detected", postgresql.JSONB(), nullable=True),
        sa.Column("page_image_key", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pages_document_id", "pages", ["document_id"])
    op.create_index("ix_pages_document_page", "pages", ["document_id", "page_number"])

    # ── extractions ──────────────────────────────────────────────────────
    op.create_table(
        "extractions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_id", sa.String(36),
                  sa.ForeignKey("pages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("extraction_type", sa.String(50), nullable=False),
        sa.Column("bbox_x0", sa.Float(), nullable=True),
        sa.Column("bbox_y0", sa.Float(), nullable=True),
        sa.Column("bbox_x1", sa.Float(), nullable=True),
        sa.Column("bbox_y1", sa.Float(), nullable=True),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("structured_data", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_reviewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reviewed_by_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("extractor_name", sa.String(100), nullable=True),
        sa.Column("extractor_version", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_extractions_document_id", "extractions", ["document_id"])
    op.create_index("ix_extractions_type", "extractions", ["extraction_type"])

    # ── quesitos ─────────────────────────────────────────────────────────
    op.create_table(
        "quesitos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36),
                  sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_quesitos_case_id", "quesitos", ["case_id"])

    # ── quesito_answers ──────────────────────────────────────────────────
    op.create_table(
        "quesito_answers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quesito_id", sa.String(36),
                  sa.ForeignKey("quesitos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("document_references", postgresql.JSONB(), nullable=True),
        sa.Column("generated_by_ai", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ai_model", sa.String(100), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_sources", postgresql.JSONB(), nullable=True),
        sa.Column("reviewed_by_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_human_reviewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("authored_by_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_quesito_answers_quesito_id", "quesito_answers", ["quesito_id"])

    # ── audit_logs ───────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("user_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("case_id", sa.String(36),
                  sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_case_id", "audit_logs", ["case_id"])
    op.create_index("ix_audit_logs_timestamp_action", "audit_logs", ["timestamp", "action"])

    # ── ai_outputs ───────────────────────────────────────────────────────
    op.create_table(
        "ai_outputs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36),
                  sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_id", sa.String(36),
                  sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quesito_id", sa.String(36),
                  sa.ForeignKey("quesitos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("output_type", sa.String(50), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=True),
        sa.Column("ai_provider", sa.String(50), nullable=False),
        sa.Column("ai_model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("structured_output", postgresql.JSONB(), nullable=True),
        sa.Column("sources", postgresql.JSONB(), nullable=True),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("review_status", sa.String(50), nullable=False),
        sa.Column("reviewed_by_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("has_documental_basis", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requested_by_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_outputs_document_id", "ai_outputs", ["document_id"])
    op.create_index("ix_ai_outputs_case_id", "ai_outputs", ["case_id"])
    op.create_index("ix_ai_outputs_review_status", "ai_outputs", ["review_status"])

    # ── page_embeddings (pgvector) ────────────────────────────────────────
    op.execute("""
        CREATE TABLE page_embeddings (
            id VARCHAR(36) PRIMARY KEY,
            page_id VARCHAR(36) NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
            document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            case_id VARCHAR(36) REFERENCES cases(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            chunk_text TEXT,
            embedding vector(1536),
            model_name VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX ix_page_embeddings_page_id ON page_embeddings(page_id)
    """)
    op.execute("""
        CREATE INDEX ix_page_embeddings_document_id ON page_embeddings(document_id)
    """)
    op.execute("""
        CREATE INDEX ix_page_embeddings_vector
        ON page_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.drop_table("page_embeddings")
    op.drop_table("ai_outputs")
    op.drop_table("audit_logs")
    op.drop_table("quesito_answers")
    op.drop_table("quesitos")
    op.drop_table("extractions")
    op.drop_table("pages")
    op.drop_table("documents")
    op.drop_table("case_parties")
    op.drop_table("cases")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
