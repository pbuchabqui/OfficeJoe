"""
Endpoints de IA: busca semântica, resumo de documento, revisão de outputs.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, require_permission
from app.core.audit import AuditAction, log_audit
from app.db.models.ai_output import AIOutput, AIReviewStatus
from app.db.models.document import Document
from app.db.models.page import Page
from app.db.session import get_db
from app.schemas.ai_output import (
    AIOutputResponse,
    AIReviewUpdate,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from app.services.ai_service import get_ai_service

router = APIRouter(prefix="/ai", tags=["IA / Busca Semântica"])


@router.post("/search", response_model=List[SemanticSearchResult])
async def semantic_search(
    payload: SemanticSearchRequest,
    current_user=Depends(require_permission("ai:query")),
    db: AsyncSession = Depends(get_db),
) -> List[SemanticSearchResult]:
    """
    Busca semântica por similaridade vetorial (pgvector).
    Retorna trechos com documento de origem e número de página.
    """
    from app.core.config import get_settings
    settings = get_settings()

    # Gera embedding da query
    from app.tasks.embedding_tasks import _get_embedding
    query_embedding = _get_embedding(payload.query, settings.EMBEDDING_MODEL)

    if query_embedding:
        # Busca vetorial
        filters = []
        params: dict = {"top_k": payload.top_k, "embedding": str(query_embedding)}

        where_clauses = []
        if payload.case_id:
            where_clauses.append("pe.case_id = :case_id")
            params["case_id"] = payload.case_id
        if payload.document_ids:
            where_clauses.append("pe.document_id = ANY(:doc_ids)")
            params["doc_ids"] = payload.document_ids

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sql = text(f"""
            SELECT
                pe.chunk_text,
                p.page_number,
                pe.document_id,
                d.display_name AS document_name,
                1 - (pe.embedding <=> :embedding::vector) AS similarity,
                pe.page_id
            FROM page_embeddings pe
            JOIN pages p ON pe.page_id = p.id
            JOIN documents d ON pe.document_id = d.id
            {where_sql}
            ORDER BY pe.embedding <=> :embedding::vector
            LIMIT :top_k
        """)
        result = await db.execute(sql, params)
        rows = result.fetchall()
    else:
        # Fallback: busca full-text simples
        q_param = f"%{payload.query}%"
        params = {"query": q_param, "top_k": payload.top_k}
        where_clauses = ["pe.chunk_text ILIKE :query"]
        if payload.case_id:
            where_clauses.append("pe.case_id = :case_id")
            params["case_id"] = payload.case_id

        sql = text(f"""
            SELECT
                pe.chunk_text,
                p.page_number,
                pe.document_id,
                d.display_name AS document_name,
                0.5 AS similarity,
                pe.page_id
            FROM page_embeddings pe
            JOIN pages p ON pe.page_id = p.id
            JOIN documents d ON pe.document_id = d.id
            WHERE {" AND ".join(where_clauses)}
            LIMIT :top_k
        """)
        result = await db.execute(sql, params)
        rows = result.fetchall()

    return [
        SemanticSearchResult(
            chunk_text=row.chunk_text or "",
            page_number=row.page_number,
            document_id=row.document_id,
            document_name=row.document_name,
            similarity=float(row.similarity),
            page_id=row.page_id,
        )
        for row in rows
    ]


@router.post("/documents/{document_id}/summarize", response_model=AIOutputResponse, status_code=201)
async def summarize_document(
    document_id: str,
    request: Request,
    current_user=Depends(require_permission("ai:query")),
    db: AsyncSession = Depends(get_db),
) -> AIOutputResponse:
    """Gera resumo estruturado de documento com rastreabilidade de páginas."""
    import uuid

    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    pages_result = await db.execute(
        select(Page)
        .where(Page.document_id == document_id, Page.raw_text.isnot(None))
        .order_by(Page.page_number)
        .limit(30)
    )
    pages_context = [
        {
            "document_id": doc.id,
            "document_name": doc.display_name or doc.original_filename,
            "page_number": p.page_number,
            "text": (p.raw_text or "")[:1500],
        }
        for p in pages_result.scalars()
    ]

    ai_service = get_ai_service()
    ai_result = ai_service.summarize_document(
        document_name=doc.display_name or doc.original_filename,
        pages_context=pages_context,
        requested_by_id=current_user.id,
    )

    output = AIOutput(
        id=str(uuid.uuid4()),
        document_id=document_id,
        case_id=doc.case_id,
        output_type=ai_result["output_type"],
        ai_provider="anthropic",
        ai_model=ai_result["ai_model"],
        prompt_tokens=ai_result.get("prompt_tokens"),
        completion_tokens=ai_result.get("completion_tokens"),
        output_text=ai_result["output_text"],
        sources=ai_result.get("sources"),
        overall_confidence=ai_result.get("overall_confidence"),
        review_status=ai_result["review_status"],
        has_documental_basis=ai_result["has_documental_basis"],
        requested_by_id=current_user.id,
        prompt_hash=ai_result.get("prompt_hash"),
    )
    db.add(output)
    await db.flush()

    return AIOutputResponse.model_validate(output)


@router.patch("/outputs/{output_id}/review", response_model=AIOutputResponse)
async def review_ai_output(
    output_id: str,
    payload: AIReviewUpdate,
    request: Request,
    current_user=Depends(require_permission("ai:review")),
    db: AsyncSession = Depends(get_db),
) -> AIOutputResponse:
    """Registra revisão humana de output de IA."""
    result = await db.execute(select(AIOutput).where(AIOutput.id == output_id))
    output = result.scalar_one_or_none()
    if not output:
        raise HTTPException(status_code=404, detail="Output não encontrado.")

    output.review_status = payload.review_status
    output.reviewed_by_id = current_user.id
    output.review_note = payload.review_note
    await db.flush()

    log_audit(
        action=AuditAction.AI_REVIEW,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="ai_output",
        resource_id=output_id,
        details={"review_status": payload.review_status},
    )

    return AIOutputResponse.model_validate(output)
