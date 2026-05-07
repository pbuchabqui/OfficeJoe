"""
Serviço de cadeia de custódia documental.

Responsabilidades:
  - Registrar eventos imutáveis sobre arquivos (record_event)
  - Verificar integridade de arquivo por comparação de hash SHA-256 (verify_file_integrity)
  - Registrar o resultado de verificação de integridade como evento de custódia
  - Listar histórico de eventos de um arquivo (list_events_for_file)

Princípio: eventos de custódia são imutáveis após criação.
A coluna updated_at não existe neste modelo por design.
"""
from __future__ import annotations

import hmac
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.custody_event import CustodyEvent, CustodyEventType
from app.db.models.document import File

logger = logging.getLogger("officejoe.custody")


# ── Registro de evento ────────────────────────────────────────────────────────

async def record_event(
    db: AsyncSession,
    *,
    file_id: str,
    event_type: CustodyEventType,
    actor_user_id: Optional[str] = None,
    actor_ip: Optional[str] = None,
    notes: Optional[str] = None,
    integrity_hash_verified: Optional[str] = None,
    integrity_ok: Optional[bool] = None,
) -> CustodyEvent:
    """
    Cria e persiste um evento de custódia imutável.

    Deve ser chamado em toda operação relevante sobre um arquivo:
    upload, download, view, verificação de integridade, etc.
    """
    event = CustodyEvent(
        id=str(uuid.uuid4()),
        file_id=file_id,
        event_type=event_type.value,
        event_at=datetime.now(timezone.utc),
        actor_user_id=actor_user_id,
        actor_ip=actor_ip,
        notes=notes,
        integrity_hash_verified=integrity_hash_verified,
        integrity_ok=integrity_ok,
    )
    db.add(event)
    await db.flush()
    logger.info(
        "Custódia: %s | file=%s | user=%s | ip=%s | ok=%s",
        event_type.value, file_id, actor_user_id, actor_ip, integrity_ok,
    )
    return event


# ── Verificação de integridade ────────────────────────────────────────────────

def verify_file_integrity(stored_hash: str, actual_hash: str) -> bool:
    """
    Compara o hash SHA-256 armazenado com o hash recém-calculado do arquivo.

    Usa hmac.compare_digest para evitar timing attacks na comparação de strings.
    Retorna True apenas se os hashes são idênticos (case-insensitive).
    """
    if not stored_hash or not actual_hash:
        return False
    return hmac.compare_digest(stored_hash.lower(), actual_hash.lower())


async def check_and_record_integrity(
    db: AsyncSession,
    *,
    file: File,
    actual_hash: str,
    actor_user_id: Optional[str] = None,
    actor_ip: Optional[str] = None,
) -> tuple[bool, CustodyEvent]:
    """
    Verifica a integridade de um arquivo e registra o resultado como evento de custódia.

    Retorna (ok, evento). Se ok=False, loga alerta crítico pois indica adulteração
    ou corrupção do arquivo original — invariante fundamental do sistema.
    """
    ok = verify_file_integrity(file.sha256_hash, actual_hash)
    event_type = (
        CustodyEventType.INTEGRITY_CHECKED if ok else CustodyEventType.INTEGRITY_FAIL
    )
    if not ok:
        logger.critical(
            "INTEGRIDADE COMPROMETIDA: file_id=%s stored=%s actual=%s",
            file.id, file.sha256_hash, actual_hash,
        )
    event = await record_event(
        db,
        file_id=file.id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_ip=actor_ip,
        integrity_hash_verified=actual_hash,
        integrity_ok=ok,
        notes=None if ok else "Hash divergente — possível adulteração ou corrupção.",
    )
    return ok, event


# ── Consulta de histórico ─────────────────────────────────────────────────────

async def list_events_for_file(
    db: AsyncSession,
    file_id: str,
) -> List[CustodyEvent]:
    """
    Retorna todos os eventos de custódia de um arquivo, em ordem cronológica.
    Ordem ascendente (event_at ASC) preserva a sequência real dos acontecimentos.
    """
    result = await db.execute(
        select(CustodyEvent)
        .where(CustodyEvent.file_id == file_id)
        .order_by(CustodyEvent.event_at.asc())
    )
    return list(result.scalars().all())


async def get_file_for_custody(
    db: AsyncSession,
    file_id: str,
) -> Optional[File]:
    """Retorna o File para operações de custódia, ou None se não existir."""
    result = await db.execute(select(File).where(File.id == file_id))
    return result.scalar_one_or_none()
