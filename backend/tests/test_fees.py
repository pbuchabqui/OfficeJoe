from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.fee import FeeCreateRequest, FeeUpdateRequest
from app.services.fee_service import (
    create_fee,
    delete_fee,
    list_fees_by_case,
    read_fee,
    update_fee,
)


@pytest.mark.asyncio
async def test_create_read_update_delete_fee(
    db_session: AsyncSession,
    sample_case,
):
    fee = await create_fee(
        db_session,
        sample_case.id,
        FeeCreateRequest(
            proposed_amount=2500.0,
            status="proposto",
            proposed_at=date(2026, 5, 7),
            notes="Proposta inicial.",
        ),
    )

    assert fee.case_id == sample_case.id
    assert fee.proposed_amount == 2500.0
    assert fee.status == "proposto"

    read = await read_fee(db_session, fee.id)
    assert read.id == fee.id

    updated = await update_fee(
        db_session,
        fee.id,
        sample_case.id,
        FeeUpdateRequest(
            arbitrated_amount=2200.0,
            status="arbitrado",
            arbitrated_at=date(2026, 5, 8),
            notes="Valor arbitrado pelo juízo.",
        ),
    )
    assert updated.arbitrated_amount == 2200.0
    assert updated.status == "arbitrado"
    assert updated.arbitrated_at == date(2026, 5, 8)

    await delete_fee(db_session, fee.id)
    with pytest.raises(ValueError, match="Fee .* not found"):
        await read_fee(db_session, fee.id)


@pytest.mark.asyncio
async def test_list_fees_filters_by_status(
    db_session: AsyncSession,
    sample_case,
):
    await create_fee(
        db_session,
        sample_case.id,
        FeeCreateRequest(proposed_amount=1000.0, status="proposto"),
    )
    await create_fee(
        db_session,
        sample_case.id,
        FeeCreateRequest(arbitrated_amount=900.0, status="arbitrado"),
    )

    all_items, total = await list_fees_by_case(db_session, sample_case.id)
    assert total == 2
    assert len(all_items) == 2

    filtered, filtered_total = await list_fees_by_case(
        db_session,
        sample_case.id,
        status="arbitrado",
    )
    assert filtered_total == 1
    assert filtered[0].status == "arbitrado"
    assert filtered[0].arbitrated_amount == 900.0


@pytest.mark.asyncio
async def test_fee_rejects_update_from_other_case(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    other_case = type(sample_case)(
        case_number="0000001-60.2024.5.02.0001",
        case_type=sample_case.case_type,
        title="Outro processo",
        status=sample_case.status,
        responsible_user_id=perito_user.id,
    )
    db_session.add(other_case)
    await db_session.flush()
    fee = await create_fee(
        db_session,
        sample_case.id,
        FeeCreateRequest(proposed_amount=1500.0, status="proposto"),
    )

    with pytest.raises(ValueError, match="does not belong to case"):
        await update_fee(
            db_session,
            fee.id,
            other_case.id,
            FeeUpdateRequest(status="arbitrado"),
        )


@pytest.mark.asyncio
async def test_fees_endpoint_crud_and_status_filter(
    client: AsyncClient,
    sample_case,
    perito_token: str,
):
    create_response = await client.post(
        f"/api/v1/fees?case_id={sample_case.id}",
        json={
            "proposed_amount": 3000.0,
            "status": "proposto",
            "proposed_at": "2026-05-07",
            "notes": "Honorários iniciais.",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert create_response.status_code == 201
    fee_id = create_response.json()["id"]

    list_response = await client.get(
        f"/api/v1/fees?case_id={sample_case.id}&fee_status=proposto",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    update_response = await client.patch(
        f"/api/v1/fees/{fee_id}?case_id={sample_case.id}",
        json={
            "deposited_amount": 3000.0,
            "status": "depositado",
            "deposited_at": "2026-05-09",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "depositado"
    assert update_response.json()["deposited_amount"] == 3000.0

    delete_response = await client.delete(
        f"/api/v1/fees/{fee_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/fees/{fee_id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert get_response.status_code == 404
