"""
Testes de auditoria: confirma geração de audit_logs para ações sensíveis.

Verifica que cada ação sobre processos produz exatamente uma entrada em
audit_logs com os campos obrigatórios preenchidos corretamente.
Usa o mesmo db_session injetado via TestClient para consultar os logs
após cada requisição HTTP.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction
from app.db.models.audit_log import AuditLog

_CASE = {
    "case_number": "1111111-11.2024.5.02.0001",
    "case_type": "trabalhista",
    "title": "Processo para teste de auditoria",
    "tribunal": "TRT-2",
    "vara": "5ª Vara do Trabalho de SP",
}


# ── helpers ───────────────────────────────────────────────────────────────────

async def _latest_log(db: AsyncSession, action: str) -> AuditLog | None:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.action == action)
        .order_by(AuditLog.timestamp.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── criação de processo ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_on_case_create(
    client: AsyncClient,
    perito_token: str,
    db_session: AsyncSession,
):
    response = await client.post(
        "/api/v1/cases",
        json=_CASE,
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 201
    case_id = response.json()["id"]

    log = await _latest_log(db_session, AuditAction.CASE_CREATED.value)

    assert log is not None, "Nenhum audit_log gerado para case.created"
    assert log.action == "case.created"
    assert log.success is True
    assert log.resource_type == "case"
    assert log.resource_id == case_id
    assert log.case_id == case_id
    assert log.user_id is not None
    assert log.user_email is not None
    assert log.details is not None
    assert log.details.get("case_number") == _CASE["case_number"]
    assert log.details.get("case_type") == _CASE["case_type"]


@pytest.mark.asyncio
async def test_audit_log_case_create_has_timestamp(
    client: AsyncClient,
    perito_token: str,
    db_session: AsyncSession,
):
    await client.post(
        "/api/v1/cases",
        json={**_CASE, "case_number": "2222222-11.2024.5.02.0001"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    log = await _latest_log(db_session, AuditAction.CASE_CREATED.value)
    assert log is not None
    assert log.timestamp is not None


# ── edição de processo ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_on_case_update(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    response = await client.patch(
        f"/api/v1/cases/{sample_case.id}",
        json={"notes": "Nota atualizada para auditoria."},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200

    log = await _latest_log(db_session, AuditAction.CASE_UPDATED.value)

    assert log is not None, "Nenhum audit_log gerado para case.updated"
    assert log.action == "case.updated"
    assert log.success is True
    assert log.resource_id == sample_case.id
    assert log.case_id == sample_case.id
    assert log.user_id is not None
    assert "old_status" in log.details


@pytest.mark.asyncio
async def test_audit_log_on_status_change(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    response = await client.patch(
        f"/api/v1/cases/{sample_case.id}",
        json={"status": "diligencias"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200

    log = await _latest_log(db_session, AuditAction.CASE_STATUS_CHANGED.value)

    assert log is not None, "Nenhum audit_log gerado para case.status_changed"
    assert log.action == "case.status_changed"
    assert log.success is True
    assert log.resource_id == sample_case.id
    assert log.details.get("status") == "diligencias"
    assert log.details.get("old_status") == "planejamento"


# ── exclusão lógica de processo ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_on_case_delete(
    client: AsyncClient,
    admin_token: str,
    sample_case,
    db_session: AsyncSession,
):
    response = await client.delete(
        f"/api/v1/cases/{sample_case.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    log = await _latest_log(db_session, AuditAction.CASE_DELETED.value)

    assert log is not None, "Nenhum audit_log gerado para case.deleted"
    assert log.action == "case.deleted"
    assert log.success is True
    assert log.resource_id == sample_case.id
    assert log.case_id == sample_case.id
    assert log.user_id is not None
    assert log.details.get("case_number") == sample_case.case_number


@pytest.mark.asyncio
async def test_audit_log_delete_action_is_not_case_updated(
    client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
):
    """Soft delete deve gerar case.deleted, nunca case.updated."""
    from app.db.models.case import Case, CaseStatus, CaseType
    import uuid

    case = Case(
        id=str(uuid.uuid4()),
        case_number="3333333-33.2024.5.02.0001",
        case_type=CaseType.CIVEL.value,
        title="Processo para verificar action de delete",
        status=CaseStatus.PLANEJAMENTO.value,
    )
    db_session.add(case)
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/cases/{case.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    log = await _latest_log(db_session, AuditAction.CASE_DELETED.value)
    assert log is not None
    assert log.action == AuditAction.CASE_DELETED.value

    # Não deve ter um log de case.updated para este case
    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == AuditAction.CASE_UPDATED.value,
            AuditLog.resource_id == case.id,
        )
    )
    assert result.scalar_one_or_none() is None


# ── campos obrigatórios ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_fields_never_null(
    client: AsyncClient,
    perito_token: str,
    db_session: AsyncSession,
):
    """action, success, timestamp nunca podem ser nulos."""
    await client.post(
        "/api/v1/cases",
        json={**_CASE, "case_number": "4444444-44.2024.5.02.0001"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    log = await _latest_log(db_session, AuditAction.CASE_CREATED.value)

    assert log is not None
    assert log.id is not None
    assert log.action is not None
    assert log.success is not None
    assert log.timestamp is not None


@pytest.mark.asyncio
async def test_audit_log_immutable_no_updated_at(db_session: AsyncSession):
    """AuditLog não deve ter coluna updated_at — é imutável por design."""
    columns = {c.key for c in AuditLog.__table__.columns}
    assert "updated_at" not in columns, (
        "AuditLog não deve ter updated_at — registros de auditoria são imutáveis"
    )
