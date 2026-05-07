# Migration 0001 — tabelas fundamentais
from app.db.models.role import Role, DEFAULT_ROLES
from app.db.models.user import User
from app.db.models.case import Case, CaseStatus, CaseType
from app.db.models.document import File, IngestionStatus
from app.db.models.custody_event import CustodyEvent, CustodyEventType
from app.db.models.audit_log import AuditLog

__all__ = [
    # Roles
    "Role", "DEFAULT_ROLES",
    # Users
    "User",
    # Cases
    "Case", "CaseStatus", "CaseType",
    # Files
    "File", "IngestionStatus",
    # Custody
    "CustodyEvent", "CustodyEventType",
    # Audit
    "AuditLog",
]
