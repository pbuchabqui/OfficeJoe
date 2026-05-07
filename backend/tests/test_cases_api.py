"""
Testes de integração para endpoints de processos periciais.

Cobre: CRUD completo, paginação, filtros por status e tipo, soft delete e RBAC.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

VALID_CASE = {
    "case_number": "9999999-00.2024.5.02.0099",
    "case_type": "trabalhista",
    "title": "Processo de Teste de Integração",
    "tribunal": "TRT-2",
    "vara": "3ª Vara do Trabalho de Campinas",
    "court_district": "Campinas",
    "fase_processual": "pericia",
    "objeto_pericia": "Apuração de verbas rescisórias e horas extras",
    "appointment_date": "2024-03-15",
    "data_ciencia": "2024-03-20",
    "deadline_date": "2024-06-15",
    "notes": "Processo urgente — prazo apertado.",
    "parties": [
        {"name": "Empresa Teste S.A.", "role": "reclamado"},
        {"name": "Trabalhador Teste", "role": "reclamante"},
    ],
}


# ── Criação ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_case(client: AsyncClient, perito_token: str):
    response = await client.post(
        "/api/v1/cases",
        json=VALID_CASE,
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["case_number"] == VALID_CASE["case_number"]
    assert data["status"] == "planejamento"
    assert data["tribunal"] == "TRT-2"
    assert data["vara"] == "3ª Vara do Trabalho de Campinas"
    assert data["fase_processual"] == "pericia"
    assert data["objeto_pericia"] == VALID_CASE["objeto_pericia"]
    assert data["appointment_date"] == "2024-03-15"
    assert data["data_ciencia"] == "2024-03-20"
    assert data["deadline_date"] == "2024-06-15"
    assert data["deleted_at"] is None
    assert len(data["parties"]) == 2


@pytest.mark.asyncio
async def test_create_case_invalid_cnj(client: AsyncClient, perito_token: str):
    """CNJ malformado deve retornar 422."""
    response = await client.post(
        "/api/v1/cases",
        json={**VALID_CASE, "case_number": "123456-invalid"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_case_invalid_type(client: AsyncClient, perito_token: str):
    response = await client.post(
        "/api/v1/cases",
        json={**VALID_CASE, "case_type": "tipo_invalido"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_case_invalid_date(client: AsyncClient, perito_token: str):
    response = await client.post(
        "/api/v1/cases",
        json={**VALID_CASE, "deadline_date": "15/06/2024"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_duplicate_case(client: AsyncClient, perito_token: str, sample_case):
    response = await client.post(
        "/api/v1/cases",
        json={**VALID_CASE, "case_number": sample_case.case_number},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 409


# ── Leitura ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_case(client: AsyncClient, perito_token: str, sample_case):
    response = await client.get(
        f"/api/v1/cases/{sample_case.id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_case.id
    assert data["case_number"] == sample_case.case_number


@pytest.mark.asyncio
async def test_get_case_not_found(client: AsyncClient, perito_token: str):
    response = await client.get(
        "/api/v1/cases/id-inexistente",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 404


# ── Listagem e paginação ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_cases_returns_pagination_envelope(client: AsyncClient, perito_token: str, sample_case):
    response = await client.get(
        "/api/v1/cases",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert "pages" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_cases_pagination(client: AsyncClient, perito_token: str, sample_case):
    response = await client.get(
        "/api/v1/cases?page=1&size=1",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["size"] == 1
    assert len(data["items"]) <= 1


@pytest.mark.asyncio
async def test_list_cases_filter_by_status(client: AsyncClient, perito_token: str, sample_case):
    response = await client.get(
        "/api/v1/cases?status=planejamento",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["status"] == "planejamento"


@pytest.mark.asyncio
async def test_list_cases_filter_by_type(client: AsyncClient, perito_token: str, sample_case):
    response = await client.get(
        "/api/v1/cases?case_type=trabalhista",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["case_type"] == "trabalhista"


@pytest.mark.asyncio
async def test_list_cases_filter_no_results(client: AsyncClient, perito_token: str, sample_case):
    response = await client.get(
        "/api/v1/cases?status=encerrado",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ── Atualização ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_case_status(client: AsyncClient, perito_token: str, sample_case):
    response = await client.patch(
        f"/api/v1/cases/{sample_case.id}",
        json={"status": "diligencias"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "diligencias"


@pytest.mark.asyncio
async def test_update_case_fields(client: AsyncClient, perito_token: str, sample_case):
    response = await client.patch(
        f"/api/v1/cases/{sample_case.id}",
        json={
            "tribunal": "TRT-15",
            "fase_processual": "instrucao",
            "notes": "Atualizado em teste.",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tribunal"] == "TRT-15"
    assert data["fase_processual"] == "instrucao"
    assert data["notes"] == "Atualizado em teste."


@pytest.mark.asyncio
async def test_update_case_invalid_status(client: AsyncClient, perito_token: str, sample_case):
    response = await client.patch(
        f"/api/v1/cases/{sample_case.id}",
        json={"status": "status_invalido"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_case_not_found(client: AsyncClient, perito_token: str):
    response = await client.patch(
        "/api/v1/cases/nao-existe",
        json={"status": "analise"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 404


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_case_soft(client: AsyncClient, perito_token: str, sample_case, admin_token: str):
    # Usar admin para deletar (precisa de case:delete)
    response = await client.delete(
        f"/api/v1/cases/{sample_case.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_deleted_case_not_in_list(client: AsyncClient, admin_token: str, db_session):
    """Case com deleted_at não deve aparecer na listagem."""
    from app.db.models.case import Case, CaseStatus, CaseType
    from datetime import datetime, timezone
    import uuid

    case = Case(
        id=str(uuid.uuid4()),
        case_number="8888888-00.2024.5.02.0001",
        case_type=CaseType.CIVEL.value,
        title="Processo Deletado",
        status=CaseStatus.PLANEJAMENTO.value,
        deleted_at=datetime.now(timezone.utc).isoformat(),
    )
    db_session.add(case)
    await db_session.flush()

    response = await client.get(
        "/api/v1/cases",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert case.id not in ids


@pytest.mark.asyncio
async def test_deleted_case_not_found_by_id(client: AsyncClient, admin_token: str, db_session):
    from app.db.models.case import Case, CaseStatus, CaseType
    from datetime import datetime, timezone
    import uuid

    case = Case(
        id=str(uuid.uuid4()),
        case_number="7777777-00.2024.5.02.0001",
        case_type=CaseType.CIVEL.value,
        title="Processo Deletado 2",
        status=CaseStatus.ENCERRADO.value,
        deleted_at=datetime.now(timezone.utc).isoformat(),
    )
    db_session.add(case)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/cases/{case.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# ── RBAC ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_leitura_cannot_create_case(client: AsyncClient, leitura_token: str):
    response = await client.post(
        "/api/v1/cases",
        json=VALID_CASE,
        headers={"Authorization": f"Bearer {leitura_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_leitura_can_read_case(client: AsyncClient, leitura_token: str, sample_case):
    response = await client.get(
        f"/api/v1/cases/{sample_case.id}",
        headers={"Authorization": f"Bearer {leitura_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_analista_cannot_delete_case(client: AsyncClient, analista_token: str, sample_case):
    response = await client.delete(
        f"/api/v1/cases/{sample_case.id}",
        headers={"Authorization": f"Bearer {analista_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_list(client: AsyncClient):
    response = await client.get("/api/v1/cases")
    assert response.status_code == 401
