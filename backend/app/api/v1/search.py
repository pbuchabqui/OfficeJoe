"""Endpoint de busca semântica."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.semantic_search import SearchQuery, SearchResponse, SearchResultItem
from app.services.semantic_search_service import semantic_search

router = APIRouter(prefix="/search", tags=["Busca Semântica"])


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Busca semântica em documentos",
)
async def search_documents(
    payload: SearchQuery,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Busca semântica em chunks de texto de documentos.

    Usa embeddings para encontrar trechos similares à query.
    Retorna os top_k resultados ordenados por similaridade.
    """
    results = await semantic_search(
        db,
        query=payload.query,
        top_k=payload.top_k,
        min_similarity=payload.min_similarity,
    )

    items = [
        SearchResultItem(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            page_number=chunk.page_number,
            text=chunk.text,
            similarity=similarity,
        )
        for chunk, similarity in results
    ]

    return SearchResponse(
        query=payload.query,
        total_results=len(items),
        results=items,
    )
