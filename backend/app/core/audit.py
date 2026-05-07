"""
Log de auditoria estruturado.
Registra toda ação relevante com usuário, IP, recurso, operação e timestamp.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger("officejoe.audit")


class AuditAction(str, Enum):
    # Autenticação
    LOGIN_SUCCESS = "auth.login_success"
    LOGIN_FAILURE = "auth.login_failure"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token_refresh"
    PASSWORD_CHANGE = "auth.password_change"

    # Documentos
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_DOWNLOAD = "document.download"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_INTEGRITY_CHECK = "document.integrity_check"
    DOCUMENT_INTEGRITY_FAIL = "document.integrity_fail"

    # OCR / Extração
    OCR_STARTED = "ocr.started"
    OCR_COMPLETED = "ocr.completed"
    OCR_FAILED = "ocr.failed"
    EXTRACTION_STARTED = "extraction.started"
    EXTRACTION_COMPLETED = "extraction.completed"

    # IA
    AI_QUERY = "ai.query"
    AI_RESPONSE = "ai.response"
    AI_REVIEW = "ai.human_review"
    DOCUMENT_CLASSIFICATION_APPROVED = "document.classification_approved"
    DOCUMENT_CLASSIFICATION_CORRECTED = "document.classification_corrected"

    # Processos / Quesitos
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_STATUS_CHANGED = "case.status_changed"
    QUESITO_CREATED = "quesito.created"
    QUESITO_ANSWERED = "quesito.answered"
    QUESITO_REVIEWED = "quesito.reviewed"

    # Usuários
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DISABLED = "user.disabled"
    ROLE_CHANGED = "user.role_changed"


class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    action: AuditAction
    user_id: Optional[str]
    user_email: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    details: Dict[str, Any]
    success: bool


def _build_entry(
    action: AuditAction,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> AuditEntry:
    return AuditEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        action=action,
        user_id=user_id,
        user_email=user_email,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details or {},
        success=success,
    )


def log_audit(
    action: AuditAction,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> AuditEntry:
    """
    Registra uma entrada de auditoria no log estruturado.
    Retorna a entrada para persistência no banco de dados.
    """
    entry = _build_entry(
        action=action,
        user_id=user_id,
        user_email=user_email,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details,
        success=success,
    )
    level = logging.INFO if success else logging.WARNING
    logger.log(
        level,
        "AUDIT %s | user=%s | resource=%s/%s | ip=%s | ok=%s | %s",
        entry.action,
        entry.user_id,
        entry.resource_type,
        entry.resource_id,
        entry.ip_address,
        entry.success,
        entry.details,
        extra={"audit_id": entry.id},
    )
    return entry
