"""Tabelas fundamentais: roles, users, cases, files, custody_events, audit_logs

Revision ID: 0001
Revises: —
Create Date: 2025-01-01 00:00:00

Escopo desta migration:
  Apenas os módulos fundamentais de identidade, custódia e auditoria.
  OCR, extração, classificação, matriz de prova, laudos e demais módulos
  são criados em migrations subsequentes.

Ordem de criação (respeita dependências de FK):
  1. roles
  2. users          (FK → roles)
  3. cases          (FK → users)
  4. files          (FK → cases, users)
  5. custody_events (FK → files, users)
  6. audit_logs     (FK → users, cases)
  + seed de roles padrão
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

    # ── 1. roles ─────────────────────────────────────────────────────────────
    # PK textual (name) elimina joins nas verificações de autorização.
    op.create_table(
        "roles",
        sa.Column("name", sa.String(30), primary_key=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column(
            "permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 2. users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.String(30),
            sa.ForeignKey("roles.name", ondelete="RESTRICT"),
            nullable=False,
            server_default="visualizador",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("otp_secret", sa.String(32), nullable=True),
        sa.Column("otp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.String(50), nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ── 3. cases ──────────────────────────────────────────────────────────────
    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_number", sa.String(100), nullable=False),
        sa.Column("case_type", sa.String(30), nullable=False),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="planejamento",
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("court", sa.String(255), nullable=True),
        sa.Column("court_district", sa.String(255), nullable=True),
        sa.Column("judge_name", sa.String(255), nullable=True),
        sa.Column("appointment_date", sa.String(20), nullable=True),
        sa.Column("deadline_date", sa.String(20), nullable=True),
        sa.Column("filing_date", sa.String(20), nullable=True),
        sa.Column("honorarium_proposed_cents", sa.Integer(), nullable=True),
        sa.Column("honorarium_approved_cents", sa.Integer(), nullable=True),
        sa.Column(
            "responsible_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_cases_case_number", "cases", ["case_number"], unique=True)
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_responsible_user_id", "cases", ["responsible_user_id"])
    op.create_index("ix_cases_deadline_date", "cases", ["deadline_date"])

    # ── 4. files ──────────────────────────────────────────────────────────────
    # Representa o arquivo original — imutável após ingestão.
    op.create_table(
        "files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=True),
        # Integridade
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "mime_type",
            sa.String(100),
            nullable=False,
            server_default="application/pdf",
        ),
        sa.Column(
            "is_original_preserved",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        # Storage
        sa.Column("storage_bucket", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        # Pipeline
        sa.Column(
            "ingestion_status",
            sa.String(30),
            nullable=False,
            server_default="received",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_pages", sa.Integer(), nullable=True),
        sa.Column("source_description", sa.Text(), nullable=True),
        sa.Column(
            "uploaded_by_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_files_case_id", "files", ["case_id"])
    op.create_index("ix_files_sha256_hash", "files", ["sha256_hash"])
    op.create_index("ix_files_ingestion_status", "files", ["ingestion_status"])
    # Detecta duplicatas dentro do mesmo processo
    op.create_index(
        "ix_files_sha256_case_unique",
        "files",
        ["sha256_hash", "case_id"],
        unique=True,
    )

    # ── 5. custody_events ─────────────────────────────────────────────────────
    # Imutável — sem updated_at.
    op.create_table(
        "custody_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "file_id",
            sa.String(36),
            sa.ForeignKey("files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_ip", sa.String(45), nullable=True),
        sa.Column("integrity_hash_verified", sa.String(64), nullable=True),
        sa.Column("integrity_ok", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Sem updated_at: registros imutáveis
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_custody_events_file_id", "custody_events", ["file_id"])
    op.create_index("ix_custody_events_event_type", "custody_events", ["event_type"])
    op.create_index("ix_custody_events_event_at", "custody_events", ["event_at"])

    # ── 6. audit_logs ─────────────────────────────────────────────────────────
    # Imutável — sem updated_at.
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        # Sem updated_at: registros imutáveis
    )
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_case_id", "audit_logs", ["case_id"])
    op.create_index(
        "ix_audit_logs_timestamp_action", "audit_logs", ["timestamp", "action"]
    )
    op.create_index(
        "ix_audit_logs_user_timestamp", "audit_logs", ["user_id", "timestamp"]
    )
    op.create_index(
        "ix_audit_logs_case_timestamp", "audit_logs", ["case_id", "timestamp"]
    )

    # ── Seed: roles padrão ────────────────────────────────────────────────────
    import json
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    roles_data = [
        {
            "name": "admin",
            "description": "Administrador do sistema — acesso irrestrito",
            "permissions": json.dumps(["*"]),
        },
        {
            "name": "perito",
            "description": "Perito responsável — acesso completo ao processo",
            "permissions": json.dumps([
                "case:read", "case:write",
                "document:read", "document:write",
                "ocr:run",
                "evidence:read", "evidence:write", "evidence:validate",
                "quesito:read", "quesito:write",
                "calc:read", "calc:write",
                "report:read", "report:write",
                "ai:query", "ai:review",
                "audit:read",
            ]),
        },
        {
            "name": "assistente",
            "description": "Assistente do perito — leitura e escrita, sem validação",
            "permissions": json.dumps([
                "case:read", "case:write",
                "document:read", "document:write",
                "ocr:run",
                "evidence:read",
                "quesito:read",
                "ai:query",
            ]),
        },
        {
            "name": "visualizador",
            "description": "Acesso somente leitura ao processo",
            "permissions": json.dumps([
                "case:read",
                "document:read",
                "evidence:read",
                "quesito:read",
            ]),
        },
    ]
    op.bulk_insert(
        sa.table(
            "roles",
            sa.column("name", sa.String),
            sa.column("description", sa.String),
            sa.column("permissions", sa.Text),
        ),
        roles_data,
    )


def downgrade() -> None:
    # Ordem inversa respeitando FKs
    op.drop_table("audit_logs")
    op.drop_table("custody_events")
    op.drop_table("files")
    op.drop_table("cases")
    op.drop_table("users")
    op.drop_table("roles")
