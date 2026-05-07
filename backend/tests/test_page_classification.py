from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.file_page import FilePage
from app.db.models.page_text_block import PageTextBlock
from app.schemas.page_classification import ClassificationAIResponse


class StubClassificationProvider:
    provider_name = "stub"
    model_name = "stub-classifier"

    async def classify_page(self, text: str) -> ClassificationAIResponse:
        assert "contrato de trabalho" in text.lower()
        return ClassificationAIResponse(
            document_class="contrato",
            confidence=0.93,
            rationale="Texto contém contrato de trabalho.",
        )


@pytest.mark.asyncio
async def test_classify_and_get_page_classification_with_mocked_provider(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "app.services.page_classification_service.get_page_classification_provider",
        lambda: StubClassificationProvider(),
    )

    document = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        original_filename="contrato.pdf",
        display_name="contrato.pdf",
        category="outro",
        sha256_hash="b" * 64,
        file_size_bytes=321,
        mime_type="application/pdf",
        storage_bucket="officejoe-documents",
        storage_key="cases/test/contrato.pdf",
        status="uploaded",
        is_original_preserved=True,
    )
    db_session.add(document)
    await db_session.flush()

    file_page = FilePage(
        id=str(uuid.uuid4()),
        file_id=document.id,
        page_number=1,
        width=595,
        height=842,
        status_ocr="completed",
        status_preview="completed",
    )
    db_session.add(file_page)
    await db_session.flush()

    db_session.add(
        PageTextBlock(
            file_page_id=file_page.id,
            file_id=document.id,
            page_number=1,
            text="Contrato de trabalho firmado entre as partes.",
            x0=0,
            y0=0,
            x1=200,
            y1=20,
            confidence=1.0,
            source="native",
        )
    )
    await db_session.flush()

    classify_response = await client.post(
        (
            f"/api/v1/cases/{sample_case.id}/documents/{document.id}"
            f"/file-pages/{file_page.id}/classification"
        ),
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert classify_response.status_code == 200
    data = classify_response.json()
    assert data["file_page_id"] == file_page.id
    assert data["file_id"] == document.id
    assert data["page_number"] == 1
    assert data["document_class"] == "contrato"
    assert data["confidence"] == pytest.approx(0.93)
    assert data["provider"] == "stub"
    assert data["model_name"] == "stub-classifier"
    assert data["raw_response"]["document_class"] == "contrato"
    assert data["human_validated"] is False
    assert data["validated_by"] is None
    assert data["validated_at"] is None

    get_response = await client.get(
        (
            f"/api/v1/cases/{sample_case.id}/documents/{document.id}"
            f"/file-pages/{file_page.id}/classification"
        ),
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert get_response.status_code == 200
    assert get_response.json()["document_class"] == "contrato"

    approve_response = await client.post(
        (
            f"/api/v1/cases/{sample_case.id}/documents/{document.id}"
            f"/file-pages/{file_page.id}/classification/approve"
        ),
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["human_validated"] is True
    assert approved["validated_by"]
    assert approved["validated_at"]
    assert approved["document_class"] == "contrato"

    correction_response = await client.patch(
        (
            f"/api/v1/cases/{sample_case.id}/documents/{document.id}"
            f"/file-pages/{file_page.id}/classification"
        ),
        json={"document_class": "laudo"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert correction_response.status_code == 200
    corrected = correction_response.json()
    assert corrected["human_validated"] is True
    assert corrected["document_class"] == "laudo"

    audit_result = await db_session.execute(
        select(AuditLog).where(AuditLog.resource_id == corrected["id"]).order_by(AuditLog.timestamp)
    )
    audit_actions = [audit.action for audit in audit_result.scalars().all()]
    assert "document.classification_approved" in audit_actions
    assert "document.classification_corrected" in audit_actions
