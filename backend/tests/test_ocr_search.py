from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.file_page import FilePage
from app.db.models.page_text_block import PageTextBlock


@pytest.mark.asyncio
async def test_search_case_ocr_text_returns_page_snippet_score_and_paginates(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    document = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        original_filename="ocr.pdf",
        display_name="ocr.pdf",
        category="outro",
        sha256_hash="a" * 64,
        file_size_bytes=123,
        mime_type="application/pdf",
        storage_bucket="officejoe-documents",
        storage_key="cases/test/ocr.pdf",
        status="uploaded",
        is_original_preserved=True,
    )
    db_session.add(document)
    await db_session.flush()

    page_one = FilePage(
        id=str(uuid.uuid4()),
        file_id=document.id,
        page_number=1,
        width=200,
        height=300,
        status_ocr="completed",
        status_preview="pending",
    )
    page_two = FilePage(
        id=str(uuid.uuid4()),
        file_id=document.id,
        page_number=2,
        width=200,
        height=300,
        status_ocr="completed",
        status_preview="pending",
    )
    db_session.add_all([page_one, page_two])
    await db_session.flush()

    db_session.add_all(
        [
            PageTextBlock(
                file_page_id=page_one.id,
                file_id=document.id,
                page_number=1,
                text="O salario base consta no recibo de pagamento.",
                x0=0,
                y0=0,
                x1=100,
                y1=10,
                confidence=0.95,
                source="native",
            ),
            PageTextBlock(
                file_page_id=page_two.id,
                file_id=document.id,
                page_number=2,
                text="Outro salario foi mencionado nos autos.",
                x0=0,
                y0=0,
                x1=100,
                y1=10,
                confidence=0.9,
                source="native",
            ),
            PageTextBlock(
                file_page_id=page_two.id,
                file_id=document.id,
                page_number=2,
                text="Texto sem a palavra buscada.",
                x0=0,
                y0=20,
                x1=100,
                y1=30,
                confidence=0.9,
                source="native",
            ),
        ]
    )
    await db_session.flush()

    response = await client.get(
        f"/api/v1/cases/{sample_case.id}/ocr-search",
        params={"q": "salario", "skip": 0, "limit": 1},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == sample_case.id
    assert data["query"] == "salario"
    assert data["skip"] == 0
    assert data["limit"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["page_number"] == 1
    assert "salario" in data["results"][0]["snippet"].lower()
    assert data["results"][0]["score"] > 0

    second_page = await client.get(
        f"/api/v1/cases/{sample_case.id}/ocr-search",
        params={"q": "salario", "skip": 1, "limit": 1},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert second_page.status_code == 200
    second_data = second_page.json()
    assert len(second_data["results"]) == 1
    assert second_data["results"][0]["page_number"] == 2
