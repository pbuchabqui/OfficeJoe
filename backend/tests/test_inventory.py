"""
Testes do inventário automático dos autos (Prompt 21).

Cobre:
- algoritmo puro de agrupamento (_group_consecutive)
- serviço generate_inventory / list_inventory
- endpoints POST e GET /{document_id}/inventory
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_inventory_item import DocumentInventoryItem
from app.db.models.file_page import FilePage
from app.db.models.page_classification import PageClassification
from app.services.inventory_service import _group_consecutive, generate_inventory, list_inventory


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_cls(page_number: int, document_class: str, confidence: float = 0.9) -> SimpleNamespace:
    """Simula um PageClassification sem persistência."""
    return SimpleNamespace(
        page_number=page_number,
        document_class=document_class,
        confidence=confidence,
    )


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


async def _make_classification(
    db: AsyncSession,
    document: Document,
    page_number: int,
    document_class: str,
    confidence: float = 0.9,
) -> PageClassification:
    file_page = FilePage(
        id=str(uuid.uuid4()),
        file_id=document.id,
        page_number=page_number,
        width=595,
        height=842,
        status_ocr="completed",
        status_preview="completed",
    )
    db.add(file_page)
    await db.flush()

    cls = PageClassification(
        id=str(uuid.uuid4()),
        file_page_id=file_page.id,
        file_id=document.id,
        page_number=page_number,
        document_class=document_class,
        confidence=confidence,
        provider="stub",
        model_name="stub-model",
    )
    db.add(cls)
    await db.flush()
    return cls


# ── _group_consecutive (função pura) ─────────────────────────────────────────

def test_group_consecutive_empty():
    assert _group_consecutive([]) == []


def test_group_consecutive_single_page():
    groups = _group_consecutive([_fake_cls(1, "holerite", 0.95)])
    assert len(groups) == 1
    assert groups[0]["document_class"] == "holerite"
    assert groups[0]["start_page"] == 1
    assert groups[0]["end_page"] == 1
    assert groups[0]["page_count"] == 1
    assert abs(groups[0]["confidence_avg"] - 0.95) < 1e-9


def test_group_consecutive_all_same_class():
    pages = [_fake_cls(i, "holerite", 0.8) for i in range(1, 6)]
    groups = _group_consecutive(pages)
    assert len(groups) == 1
    assert groups[0]["start_page"] == 1
    assert groups[0]["end_page"] == 5
    assert groups[0]["page_count"] == 5
    assert abs(groups[0]["confidence_avg"] - 0.8) < 1e-9


def test_group_consecutive_alternating_classes():
    pages = [
        _fake_cls(1, "holerite"),
        _fake_cls(2, "sentença"),
        _fake_cls(3, "holerite"),
    ]
    groups = _group_consecutive(pages)
    assert len(groups) == 3
    assert [g["document_class"] for g in groups] == ["holerite", "sentença", "holerite"]
    assert [g["page_count"] for g in groups] == [1, 1, 1]


def test_group_consecutive_realistic_scenario():
    """Holerites (pp.1-3), decisão (p.4), extrato (pp.5-6)."""
    pages = [
        _fake_cls(1, "holerite", 0.95),
        _fake_cls(2, "holerite", 0.90),
        _fake_cls(3, "holerite", 0.85),
        _fake_cls(4, "decisão", 0.99),
        _fake_cls(5, "extrato", 0.80),
        _fake_cls(6, "extrato", 0.75),
    ]
    groups = _group_consecutive(pages)
    assert len(groups) == 3

    holerite, decisao, extrato = groups
    assert holerite["document_class"] == "holerite"
    assert holerite["start_page"] == 1
    assert holerite["end_page"] == 3
    assert holerite["page_count"] == 3
    assert abs(holerite["confidence_avg"] - (0.95 + 0.90 + 0.85) / 3) < 1e-9

    assert decisao["document_class"] == "decisão"
    assert decisao["start_page"] == 4
    assert decisao["end_page"] == 4
    assert decisao["page_count"] == 1

    assert extrato["document_class"] == "extrato"
    assert extrato["start_page"] == 5
    assert extrato["end_page"] == 6
    assert extrato["page_count"] == 2


def test_group_consecutive_confidence_average():
    pages = [_fake_cls(1, "contrato", 0.6), _fake_cls(2, "contrato", 1.0)]
    groups = _group_consecutive(pages)
    assert abs(groups[0]["confidence_avg"] - 0.8) < 1e-9


# ── generate_inventory / list_inventory (async, banco) ───────────────────────

@pytest.mark.asyncio
async def test_generate_inventory_empty_when_no_classifications(
    db_session: AsyncSession, sample_case
):
    doc = await _make_document(db_session, sample_case.id)
    items = await generate_inventory(db_session, doc.id)
    assert items == []


@pytest.mark.asyncio
async def test_generate_inventory_creates_correct_groups(
    db_session: AsyncSession, sample_case
):
    doc = await _make_document(db_session, sample_case.id)
    await _make_classification(db_session, doc, 1, "holerite", 0.9)
    await _make_classification(db_session, doc, 2, "holerite", 0.8)
    await _make_classification(db_session, doc, 3, "sentença", 0.95)

    items = await generate_inventory(db_session, doc.id)
    assert len(items) == 2
    assert items[0].document_class == "holerite"
    assert items[0].start_page == 1
    assert items[0].end_page == 2
    assert items[0].page_count == 2
    assert items[1].document_class == "sentença"
    assert items[1].start_page == 3
    assert items[1].end_page == 3
    assert items[1].page_count == 1


@pytest.mark.asyncio
async def test_generate_inventory_replaces_previous(
    db_session: AsyncSession, sample_case
):
    """Segunda geração deve substituir a primeira completamente."""
    doc = await _make_document(db_session, sample_case.id)
    await _make_classification(db_session, doc, 1, "holerite")
    await _make_classification(db_session, doc, 2, "holerite")

    first = await generate_inventory(db_session, doc.id)
    assert len(first) == 1

    # Adiciona nova página com classe diferente e regenera
    await _make_classification(db_session, doc, 3, "contrato")
    second = await generate_inventory(db_session, doc.id)
    assert len(second) == 2

    # Confirma que no banco só existem os itens da segunda geração
    result = await db_session.execute(
        select(DocumentInventoryItem).where(
            DocumentInventoryItem.document_id == doc.id
        )
    )
    persisted = result.scalars().all()
    assert len(persisted) == 2


@pytest.mark.asyncio
async def test_generate_inventory_persists_to_db(
    db_session: AsyncSession, sample_case
):
    doc = await _make_document(db_session, sample_case.id)
    await _make_classification(db_session, doc, 1, "laudo", 0.99)

    await generate_inventory(db_session, doc.id)

    result = await db_session.execute(
        select(DocumentInventoryItem).where(
            DocumentInventoryItem.document_id == doc.id
        )
    )
    items = result.scalars().all()
    assert len(items) == 1
    assert items[0].document_class == "laudo"
    assert items[0].generated_at is not None


@pytest.mark.asyncio
async def test_list_inventory_empty_before_generation(
    db_session: AsyncSession, sample_case
):
    doc = await _make_document(db_session, sample_case.id)
    items = await list_inventory(db_session, doc.id)
    assert items == []


@pytest.mark.asyncio
async def test_list_inventory_returns_ordered_by_start_page(
    db_session: AsyncSession, sample_case
):
    doc = await _make_document(db_session, sample_case.id)
    await _make_classification(db_session, doc, 1, "holerite")
    await _make_classification(db_session, doc, 2, "contrato")
    await _make_classification(db_session, doc, 3, "extrato")

    await generate_inventory(db_session, doc.id)
    items = await list_inventory(db_session, doc.id)

    assert len(items) == 3
    for i in range(len(items) - 1):
        assert items[i].start_page <= items[i + 1].start_page


# ── endpoints HTTP ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_inventory_returns_200_with_groups(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    await _make_classification(db_session, doc, 1, "holerite", 0.9)
    await _make_classification(db_session, doc, 2, "holerite", 0.8)
    await _make_classification(db_session, doc, 3, "sentença", 0.95)

    resp = await client.post(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == doc.id
    assert body["total_groups"] == 2
    assert body["items"][0]["document_class"] == "holerite"
    assert body["items"][0]["start_page"] == 1
    assert body["items"][0]["end_page"] == 2
    assert body["items"][1]["document_class"] == "sentença"


@pytest.mark.asyncio
async def test_post_inventory_empty_when_no_classifications(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    resp = await client.post(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total_groups"] == 0
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_get_inventory_returns_existing_items(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    await _make_classification(db_session, doc, 1, "laudo", 0.99)

    # Gera via POST
    await client.post(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory",
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    # Lista via GET
    resp = await client.get(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_groups"] == 1
    assert body["items"][0]["document_class"] == "laudo"


@pytest.mark.asyncio
async def test_get_inventory_empty_before_generation(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    resp = await client.get(
        f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total_groups"] == 0


@pytest.mark.asyncio
async def test_inventory_404_for_unknown_document(
    client: AsyncClient,
    perito_token: str,
    sample_case,
):
    fake_id = str(uuid.uuid4())
    for method in (client.post, client.get):
        resp = await method(
            f"/api/v1/cases/{sample_case.id}/documents/{fake_id}/inventory",
            headers={"Authorization": f"Bearer {perito_token}"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_inventory_404_for_wrong_case(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    """Documento de outro caso não deve ser acessível via case_id errado."""
    doc = await _make_document(db_session, sample_case.id)
    wrong_case_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/v1/cases/{wrong_case_id}/documents/{doc.id}/inventory",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_inventory_requires_auth(
    client: AsyncClient,
    sample_case,
    db_session: AsyncSession,
):
    doc = await _make_document(db_session, sample_case.id)
    for method in (client.post, client.get):
        resp = await method(
            f"/api/v1/cases/{sample_case.id}/documents/{doc.id}/inventory"
        )
        assert resp.status_code == 401
