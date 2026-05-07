"""
Testes de edição manual do inventário (Prompt 22).

Cobre:
- atualização de custom_label, document_class, start_page/end_page, is_relevant
- validação de integridade (start_page <= end_page)
- auditoria de mudanças
- endpoints HTTP, auth e 404
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction
from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.document_inventory_item import DocumentInventoryItem
from app.db.models.file_page import FilePage
from app.db.models.page_classification import PageClassification


async def _make_document(db: AsyncSession, case_id: str) -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=case_id,
        original_filename="autos.pdf",
        display_name="autos.pdf",
        category="outro",
        sha256_hash="a" * 64,
        file_size_bytes=1024,
        mime_type="application/pdf",
        storage_bucket="officejoe-documents",
        storage_key=f"cases/{case_id}/autos.pdf",
        status="uploaded",
        is_original_preserved=True,
    )
    db.add(doc)
    await db.flush()
    return doc


async def _make_inventory_item(
    db: AsyncSession,
    document: Document,
    start_page: int = 1,
    end_page: int = 1,
    document_class: str = "holerite",
) -> DocumentInventoryItem:
    item = DocumentInventoryItem(
        id=str(uuid.uuid4()),
        document_id=document.id,
        document_class=document_class,
        start_page=start_page,
        end_page=end_page,
        page_count=end_page - start_page + 1,
        confidence_avg=0.9,
    )
    db.add(item)
    await db.flush()
    return item


# ── Testes de atualização básica ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_custom_label(db_session: AsyncSession, sample_case):
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 2)

    assert item.custom_label is None
    item.custom_label = "Holerites Favoráveis"
    await db_session.flush()

    result = await db_session.get(DocumentInventoryItem, item.id)
    assert result.custom_label == "Holerites Favoráveis"


@pytest.mark.asyncio
async def test_update_document_class(db_session: AsyncSession, sample_case):
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 2, "holerite")

    item.document_class = "sentença"
    await db_session.flush()

    result = await db_session.get(DocumentInventoryItem, item.id)
    assert result.document_class == "sentença"


@pytest.mark.asyncio
async def test_update_page_range(db_session: AsyncSession, sample_case):
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 3)

    item.start_page = 1
    item.end_page = 5
    item.page_count = 5
    await db_session.flush()

    result = await db_session.get(DocumentInventoryItem, item.id)
    assert result.start_page == 1
    assert result.end_page == 5
    assert result.page_count == 5


@pytest.mark.asyncio
async def test_update_is_relevant(db_session: AsyncSession, sample_case):
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 1)

    assert item.is_relevant is True
    item.is_relevant = False
    await db_session.flush()

    result = await db_session.get(DocumentInventoryItem, item.id)
    assert result.is_relevant is False


# ── Testes HTTP de edição ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_inventory_item_custom_label(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 2)

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{item.id}",
        json={"custom_label": "Documentação Financeira"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["custom_label"] == "Documentação Financeira"


@pytest.mark.asyncio
async def test_patch_inventory_item_class_and_relevance(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 1, "holerite")

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{item.id}",
        json={"document_class": "extrato", "is_relevant": False},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_class"] == "extrato"
    assert body["is_relevant"] is False


@pytest.mark.asyncio
async def test_patch_inventory_item_page_range(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 5)

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{item.id}",
        json={"start_page": 2, "end_page": 7},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["start_page"] == 2
    assert body["end_page"] == 7
    assert body["page_count"] == 6


@pytest.mark.asyncio
async def test_patch_inventory_item_no_changes(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    """Payload sem mudanças retorna item inalterado."""
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 1, "holerite")

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{item.id}",
        json={},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["document_class"] == "holerite"


# ── Validação ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_inventory_item_invalid_range(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    """start_page > end_page deve retornar 400."""
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 5)

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{item.id}",
        json={"start_page": 10, "end_page": 5},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 400
    assert "não pode ser maior" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_inventory_item_negative_page(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    """Página negativa deve falhar na validação do schema."""
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 1)

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{item.id}",
        json={"start_page": -1},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 422


# ── Auditoria ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_inventory_item_creates_audit_log(
    client: AsyncClient,
    perito_token: str,
    perito_user,
    sample_case,
    db_session: AsyncSession,
):
    """Edição deve registrar AuditLog com before/after das mudanças."""
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 3, "holerite")

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{item.id}",
        json={"document_class": "sentença", "is_relevant": False},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200

    # Verifica auditoria
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.user_id == perito_user.id)
        .where(AuditLog.action == AuditAction.INVENTORY_ITEM_EDITED.value)
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.resource_type == "inventory_item"
    assert audit.resource_id == item.id
    assert "changes" in audit.details
    changes = audit.details["changes"]
    assert "document_class" in changes
    assert changes["document_class"]["before"] == "holerite"
    assert changes["document_class"]["after"] == "sentença"
    assert "is_relevant" in changes


# ── Erro 404 ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_inventory_item_404_unknown_item(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    fake_item_id = str(uuid.uuid4())

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{fake_item_id}",
        json={"custom_label": "Teste"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_inventory_item_404_wrong_document(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    """Item de outro documento não é acessível."""
    doc1 = await _make_document(db_session, sample_case.id)
    doc2 = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc1, 1, 1)

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc2.id}/inventory/{item.id}",
        json={"custom_label": "Teste"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_inventory_item_404_wrong_case(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    """Documento de outro caso não é acessível."""
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 1)
    wrong_case_id = str(uuid.uuid4())

    resp = await client.patch(
        f"/api/v1/cases/{wrong_case_id}/documents/{doc.id}/inventory/{item.id}",
        json={"custom_label": "Teste"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 404


# ── Autenticação ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_inventory_item_requires_auth(
    client: AsyncClient,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    item = await _make_inventory_item(db_session, doc, 1, 1)

    resp = await client.patch(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory/{item.id}",
        json={"custom_label": "Teste"},
    )
    assert resp.status_code == 401
