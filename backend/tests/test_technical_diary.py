from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.technical_diary import (
    TechnicalDiaryEntryCreateRequest,
    TechnicalDiaryEntryUpdateRequest,
)
from app.services.technical_diary_service import (
    create_technical_diary_entry,
    delete_technical_diary_entry,
    list_technical_diary_entries_by_case,
    read_technical_diary_entry,
    update_technical_diary_entry,
)


@pytest.mark.asyncio
async def test_create_read_update_delete_technical_diary_entry(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    entry = await create_technical_diary_entry(
        db_session,
        sample_case.id,
        TechnicalDiaryEntryCreateRequest(
            entry_date=date(2026, 5, 7),
            responsible_user_id=perito_user.id,
            decision_type="criterio_tecnico",
            description="Adotar critério conservador para rubrica sem detalhamento.",
            technical_justification="Documentação disponível não separa a rubrica por origem.",
            status="draft",
        ),
    )

    assert entry.case_id == sample_case.id
    assert entry.responsible_user_id == perito_user.id
    assert entry.decision_type == "criterio_tecnico"

    read_entry = await read_technical_diary_entry(db_session, entry.id)
    assert read_entry.id == entry.id

    updated = await update_technical_diary_entry(
        db_session,
        entry.id,
        sample_case.id,
        TechnicalDiaryEntryUpdateRequest(
            status="final",
            description="Critério técnico atualizado.",
        ),
    )
    assert updated.status == "final"
    assert updated.description == "Critério técnico atualizado."

    await delete_technical_diary_entry(db_session, entry.id)
    with pytest.raises(ValueError, match="Technical diary entry .* not found"):
        await read_technical_diary_entry(db_session, entry.id)


@pytest.mark.asyncio
async def test_list_technical_diary_entries_filters_by_case_type_and_status(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    await create_technical_diary_entry(
        db_session,
        sample_case.id,
        TechnicalDiaryEntryCreateRequest(
            entry_date=date(2026, 5, 1),
            responsible_user_id=perito_user.id,
            decision_type="criterio_tecnico",
            description="Primeira decisão.",
            technical_justification="Justificativa técnica.",
            status="draft",
        ),
    )
    await create_technical_diary_entry(
        db_session,
        sample_case.id,
        TechnicalDiaryEntryCreateRequest(
            entry_date=date(2026, 5, 2),
            responsible_user_id=perito_user.id,
            decision_type="limitacao",
            description="Segunda decisão.",
            technical_justification="Outra justificativa técnica.",
            status="final",
        ),
    )

    all_items, total = await list_technical_diary_entries_by_case(db_session, sample_case.id)
    assert total == 2
    assert [item.entry_date for item in all_items] == [date(2026, 5, 2), date(2026, 5, 1)]

    filtered_by_type, type_total = await list_technical_diary_entries_by_case(
        db_session,
        sample_case.id,
        decision_type="criterio_tecnico",
    )
    assert type_total == 1
    assert filtered_by_type[0].decision_type == "criterio_tecnico"

    filtered_by_status, status_total = await list_technical_diary_entries_by_case(
        db_session,
        sample_case.id,
        status="final",
    )
    assert status_total == 1
    assert filtered_by_status[0].status == "final"


@pytest.mark.asyncio
async def test_technical_diary_endpoint_crud_and_filters(
    client: AsyncClient,
    sample_case,
    perito_user,
    perito_token: str,
):
    create_response = await client.post(
        f"/api/v1/technical-diary?case_id={sample_case.id}",
        json={
            "entry_date": "2026-05-07",
            "responsible_user_id": perito_user.id,
            "decision_type": "criterio_tecnico",
            "description": "Registrar decisão técnica.",
            "technical_justification": "Justificativa baseada nos documentos disponíveis.",
            "status": "draft",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert create_response.status_code == 201
    entry_id = create_response.json()["id"]

    list_response = await client.get(
        f"/api/v1/technical-diary?case_id={sample_case.id}&decision_type=criterio_tecnico&entry_status=draft",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    update_response = await client.patch(
        f"/api/v1/technical-diary/{entry_id}?case_id={sample_case.id}",
        json={"status": "final"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "final"

    delete_response = await client.delete(
        f"/api/v1/technical-diary/{entry_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/technical-diary/{entry_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert get_response.status_code == 404
