"""
Serviço de auditoria.

Ponto único de entrada para registrar e persistir entradas de audit_logs.
Encapsula a criação do AuditEntry (log estruturado) e a persistência no banco
em uma única chamada async, mantendo os endpoints finos.

Princípio de resiliência: falhas de auditoria NUNCA propagam exceção para o
caller — o log de erro no Python logger é o mecanismo de alerta.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, AuditEntry, log_audit
from app.db.models.audit_log import AuditLog

logger = logging.getLogger("officejoe.audit_service")


async def record_audit(
    db: AsyncSession,
    *,
    action: AuditAction,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    case_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> Optional[AuditEntry]:
    """
    Cria e persiste uma entrada de auditoria.

    Retorna o AuditEntry gerado, ou None em caso de falha (que é registrada
    no logger de erro sem re-lançar a exceção).
    """
    entry = log_audit(
        action=action,
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        success=success,
    )
    try:
        log = AuditLog(
            id=entry.id,
            timestamp=entry.timestamp,
            action=entry.action.value,
            success=entry.success,
            user_id=entry.user_id,
            user_email=entry.user_email,
            ip_address=entry.ip_address,
            user_agent=user_agent,
            case_id=case_id,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            details=entry.details,
        )
        db.add(log)
        await db.flush()
        return entry
    except Exception as exc:
        logger.error(
            "Falha ao persistir audit log (action=%s user=%s): %s",
            action.value, user_id, exc,
        )
        return None
