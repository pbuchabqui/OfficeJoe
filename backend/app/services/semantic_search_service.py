"""Orquestração de busca semântica: chunking + embedding + busca."""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.text_chunk import TextChunk
from app.services.chunking_service import chunk_text
from app.services.embedding_service import MockEmbedding

logger = logging.getLogger("officejoe.search")


async def index_document(
    db: AsyncSession,
    document_id: str,
    text: str,
    page_number: int,
) -> int:
    """
    Indexa um documento: divide em chunks, gera embeddings e persiste.

    Args:
        db: Sessão do banco
        document_id: ID do documento
        text: Texto a indexar
        page_number: Número da página no documento

    Returns:
        Número de chunks criados
    """
    # Remove chunks antigos desta página
    await db.execute(
        select(TextChunk).where(
            and_(
                TextChunk.document_id == document_id,
                TextChunk.page_number == page_number,
            )
        )
    )
    result = await db.execute(
        select(TextChunk).where(
            and_(
                TextChunk.document_id == document_id,
                TextChunk.page_number == page_number,
            )
        )
    )
    old_chunks = result.scalars().all()
    for chunk in old_chunks:
        await db.delete(chunk)

    # Divide em chunks
    chunks = chunk_text(text)

    # Cria registros de chunk com embeddings
    created_count = 0
    for chunk_text_content in chunks:
        embedding = MockEmbedding.embed(chunk_text_content)

        chunk_record = TextChunk(
            document_id=document_id,
            page_number=page_number,
            text=chunk_text_content,
            embedding=embedding,
        )
        db.add(chunk_record)
        created_count += 1

    await db.flush()

    logger.info(
        "Indexado documento %s página %d: %d chunks",
        document_id,
        page_number,
        created_count,
    )

    return created_count


async def semantic_search(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.3,
) -> List[tuple[TextChunk, float]]:
    """
    Busca semântica: encontra chunks similares à query.

    Args:
        db: Sessão do banco
        query: Texto da busca
        top_k: Número de resultados
        min_similarity: Score mínimo de similaridade

    Returns:
        Lista de (chunk, score) ordenada por score descendente
    """
    # Gera embedding da query
    query_embedding = MockEmbedding.embed(query)

    # Busca todos os chunks (em produção usaria pgvector native)
    result = await db.execute(select(TextChunk))
    all_chunks = result.scalars().all()

    # Calcula similaridade com cada chunk
    scored_chunks: list[tuple[TextChunk, float]] = []
    for chunk in all_chunks:
        similarity = MockEmbedding.similarity(query_embedding, chunk.embedding)
        if similarity >= min_similarity:
            scored_chunks.append((chunk, similarity))

    # Ordena por score descendente e retorna top_k
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    results = scored_chunks[:top_k]

    logger.info(
        "Busca semântica por '%s': %d resultados encontrados",
        query[:50],
        len(results),
    )

    return results
