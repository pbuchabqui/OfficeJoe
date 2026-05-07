"""Testes de busca semântica com embeddings mockados."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.text_chunk import TextChunk
from app.services.chunking_service import chunk_text
from app.services.embedding_service import MockEmbedding
from app.services.semantic_search_service import semantic_search, index_document


# ── Serviço de chunking ───────────────────────────────────────────────────────

def test_chunk_text_empty():
    """Texto vazio retorna lista vazia."""
    assert chunk_text("") == []


def test_chunk_text_single_chunk():
    """Texto pequeno retorna um único chunk."""
    text = "Pequeno texto."
    chunks = chunk_text(text, chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_multiple_chunks():
    """Texto grande é dividido em múltiplos chunks."""
    text = " ".join(["palavra"] * 200)  # ~1200 caracteres
    chunks = chunk_text(text, chunk_size=500)
    assert len(chunks) > 1


def test_chunk_text_respects_sentences():
    """Tenta quebrar em limites de sentença."""
    text = "Primeira sentença. Segunda sentença. Terceira sentença."
    chunks = chunk_text(text, chunk_size=100)
    # Cada chunk deve tentar terminar em sentença
    for chunk in chunks:
        assert chunk[-1] in '.!?' or len(chunk) >= 100


def test_chunk_text_removes_empty():
    """Chunks vazios são removidos."""
    text = "   \n   \n   "
    chunks = chunk_text(text)
    assert len(chunks) == 0


# ── Serviço de embeddings ─────────────────────────────────────────────────────

def test_embedding_deterministic():
    """Mesmo texto produz mesmo embedding."""
    text = "Texto de teste para embeddings"
    emb1 = MockEmbedding.embed(text)
    emb2 = MockEmbedding.embed(text)
    assert emb1 == emb2


def test_embedding_dimension():
    """Embedding tem dimensão correta."""
    emb = MockEmbedding.embed("qualquer texto")
    assert len(emb) == MockEmbedding.DIMENSION
    assert len(emb) == 384


def test_embedding_normalized():
    """Embedding é normalizado (magnitude ~1)."""
    emb = MockEmbedding.embed("texto para teste")
    magnitude = sum(x ** 2 for x in emb) ** 0.5
    assert 0.99 < magnitude < 1.01  # Margem pequena para arredondamento


def test_embedding_different_texts():
    """Textos diferentes produzem embeddings diferentes."""
    emb1 = MockEmbedding.embed("texto um")
    emb2 = MockEmbedding.embed("texto dois")
    assert emb1 != emb2


def test_similarity_identical():
    """Similaridade de texto idêntico é ~1."""
    text = "Texto para teste"
    emb = MockEmbedding.embed(text)
    similarity = MockEmbedding.similarity(emb, emb)
    assert 0.9 < similarity <= 1.0


def test_similarity_symmetric():
    """Similaridade é simétrica."""
    emb1 = MockEmbedding.embed("texto um")
    emb2 = MockEmbedding.embed("texto dois")
    sim1 = MockEmbedding.similarity(emb1, emb2)
    sim2 = MockEmbedding.similarity(emb2, emb1)
    assert sim1 == sim2


def test_similarity_range():
    """Similaridade está em [0, 1]."""
    emb1 = MockEmbedding.embed("primeira texto")
    emb2 = MockEmbedding.embed("segunda mensagem completamente diferente")
    similarity = MockEmbedding.similarity(emb1, emb2)
    assert 0 <= similarity <= 1


# ── Serviço de busca semântica ────────────────────────────────────────────────

async def _make_document(db: AsyncSession, case_id: str) -> Document:
    doc = Document(
        id=str(uuid.uuid4()),
        case_id=case_id,
        original_filename="test.pdf",
        display_name="test.pdf",
        category="outro",
        sha256_hash="a" * 64,
        file_size_bytes=1024,
        mime_type="application/pdf",
        storage_bucket="test-bucket",
        storage_key="test-key",
        status="uploaded",
        is_original_preserved=True,
    )
    db.add(doc)
    await db.flush()
    return doc


@pytest.mark.asyncio
async def test_index_document_empty_text(db_session: AsyncSession, sample_case):
    """Indexar texto vazio não cria chunks."""
    doc = await _make_document(db_session, sample_case.id)
    count = await index_document(db_session, doc.id, "", 1)
    assert count == 0


@pytest.mark.asyncio
async def test_index_document_creates_chunks(db_session: AsyncSession, sample_case):
    """Indexação cria chunks e embeddings."""
    doc = await _make_document(db_session, sample_case.id)
    text = " ".join(["palavra"] * 200)  # Texto grande
    count = await index_document(db_session, doc.id, text, 1)
    assert count > 0


@pytest.mark.asyncio
async def test_index_document_persists(db_session: AsyncSession, sample_case):
    """Chunks são persistidos no banco."""
    doc = await _make_document(db_session, sample_case.id)
    text = "Primeiro chunk. Segundo chunk. Terceiro chunk."
    await index_document(db_session, doc.id, text, 1)

    # Verifica chunks no banco
    from sqlalchemy import select
    result = await db_session.execute(
        select(TextChunk).where(TextChunk.document_id == doc.id)
    )
    chunks = result.scalars().all()
    assert len(chunks) > 0
    assert all(chunk.embedding is not None for chunk in chunks)


@pytest.mark.asyncio
async def test_semantic_search_empty(db_session: AsyncSession, sample_case):
    """Busca em banco vazio retorna lista vazia."""
    results = await semantic_search(db_session, "query qualquer")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_semantic_search_finds_similar(db_session: AsyncSession, sample_case):
    """Busca encontra texto similar."""
    doc = await _make_document(db_session, sample_case.id)
    await index_document(db_session, doc.id, "Salário base é R$ 2.500,00. Bônus é R$ 500,00.", 1)

    results = await semantic_search(db_session, "salário", top_k=5)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_semantic_search_respects_top_k(db_session: AsyncSession, sample_case):
    """Busca respeita limite top_k."""
    doc = await _make_document(db_session, sample_case.id)
    text = ". ".join([f"Texto {i}" for i in range(20)])
    await index_document(db_session, doc.id, text, 1)

    results = await semantic_search(db_session, "texto", top_k=3)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_semantic_search_respects_min_similarity(db_session: AsyncSession, sample_case):
    """Busca filtra por similaridade mínima."""
    doc = await _make_document(db_session, sample_case.id)
    await index_document(db_session, doc.id, "Texto não relacionado qualquer coisa", 1)

    # Busca com threshold alto não encontra
    results = await semantic_search(db_session, "xyz", min_similarity=0.95)
    # Pode encontrar ou não, mas score deve estar acima de 0.95
    for chunk, score in results:
        assert score >= 0.95


# ── Endpoint HTTP ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_endpoint_success(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    """Endpoint de busca retorna resultados."""
    doc = await _make_document(db_session, sample_case.id)
    await index_document(db_session, doc.id, "Holerite salário mensal contrato", 1)

    resp = await client.post(
        "/api/v1/search",
        json={"query": "salário", "top_k": 5},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "query" in body
    assert "results" in body
    assert "total_results" in body


@pytest.mark.asyncio
async def test_search_endpoint_empty_results(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
):
    """Busca em banco vazio retorna lista vazia."""
    resp = await client.post(
        "/api/v1/search",
        json={"query": "xyz", "top_k": 5},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_results"] == 0
    assert body["results"] == []


@pytest.mark.asyncio
async def test_search_endpoint_requires_auth(client: AsyncClient):
    """Endpoint requer autenticação."""
    resp = await client.post(
        "/api/v1/search",
        json={"query": "teste", "top_k": 5},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_endpoint_invalid_query(
    client: AsyncClient,
    perito_token: str,
):
    """Query vazia é inválida."""
    resp = await client.post(
        "/api/v1/search",
        json={"query": "", "top_k": 5},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert resp.status_code == 422
