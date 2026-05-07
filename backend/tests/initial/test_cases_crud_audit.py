from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog


INITIAL_CASE_PAYLOAD = {
    "case_number": "0000062-00.2026.5.02.0001",
    "case_type": "trabalhista",
    "title": "Processo inicial de testes",
    "description": "Cobertura inicial de CRUD de processos.",
    "court": "1ª Vara do Trabalho",
    "parties": [
        {"name": "Reclamante Teste", "role": "reclamante"},
        {"name": "Empresa Teste", "role": "reclamado"},
    ],
}


@pytest.mark.asyncio
async def test_cases_crud_and_process_audit(
    client: AsyncClient,
    perito_token: str,
    admin_token: str,
    db_session: AsyncSession,
):
    create_response = await client.post(
        "/api/v1/cases",
        json=INITIAL_CASE_PAYLOAD,
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    case_id = created["id"]
    assert created["case_number"] == INITIAL_CASE_PAYLOAD["case_number"]
    assert created["status"] == "planejamento"
    assert len(created["parties"]) == 2

    read_response = await client.get(
        f"/api/v1/cases/{case_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert read_response.status_code == 200
    assert read_response.json()["id"] == case_id

    update_response = await client.patch(
        f"/api/v1/cases/{case_id}",
        json={"status": "diligencias"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "diligencias"

    list_response = await client.get(
        "/api/v1/cases?status=diligencias",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert list_response.status_code == 200
    assert any(item["id"] == case_id for item in list_response.json())

    audit_result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.case_id == case_id)
        .order_by(AuditLog.timestamp)
    )
    audit_actions = [log.action for log in audit_result.scalars().all()]
    assert "case.created" in audit_actions
    assert "case.status_changed" in audit_actions

    delete_response = await client.delete(
        f"/api/v1/cases/{case_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 204

    missing_response = await client.get(
        f"/api/v1/cases/{case_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert missing_response.status_code == 404
