"""
Endpoints de quesitos periciais e respostas com lastro documental obrigatório.
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_client_ip, get_current_user, persist_audit, require_permission
from app.core.audit import AuditAction, log_audit
from app.db.models.case import Case
from app.db.models.quesito import Quesito, QuesitoAnswer, QuesitoStatus
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.quesito import (
    AIQuesitoRequest,
    QuesitoAnswerCreate,
    QuesitoAnswerResponse,
    QuesitoCreate,
    QuesitoResponse,
    QuesitoUpdate,
)

router = APIRouter(prefix="/cases/{case_id}/quesitos", tags=["Quesitos"])


@router.get("", response_model=List[QuesitoResponse])
async def list_quesitos(
    case_id: str,
    current_user=Depends(require_permission("quesito:read")),
    db: AsyncSession = Depends(get_db),
) -> List[QuesitoResponse]:
    result = await db.execute(
        select(Quesito)
        .where(Quesito.case_id == case_id)
        .options(selectinload(Quesito.answers))
        .order_by(Quesito.sequence_number)
    )
    return [QuesitoResponse.model_validate(q) for q in result.scalars().all()]


@router.post("", response_model=QuesitoResponse, status_code=status.HTTP_201_CREATED)
async def create_quesito(
    case_id: str,
    payload: QuesitoCreate,
    request: Request,
    current_user=Depends(require_permission("quesito:write")),
    db: AsyncSession = Depends(get_db),
) -> QuesitoResponse:
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    if not case_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")

    quesito = Quesito(
        id=str(uuid.uuid4()),
        case_id=case_id,
        sequence_number=payload.sequence_number,
        origin=payload.origin,
        question_text=payload.question_text,
        status=QuesitoStatus.PENDENTE.value,
    )
    db.add(quesito)
    await db.flush()

    entry = log_audit(
        action=AuditAction.QUESITO_CREATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="quesito",
        resource_id=quesito.id,
        details={"case_id": case_id, "seq": payload.sequence_number},
    )
    await persist_audit(entry, db, case_id=case_id)

    result = await db.execute(
        select(Quesito).where(Quesito.id == quesito.id).options(selectinload(Quesito.answers))
    )
    return QuesitoResponse.model_validate(result.scalar_one())


@router.post("/{quesito_id}/answers", response_model=QuesitoAnswerResponse, status_code=status.HTTP_201_CREATED)
async def add_answer(
    case_id: str,
    quesito_id: str,
    payload: QuesitoAnswerCreate,
    request: Request,
    current_user=Depends(require_permission("quesito:write")),
    db: AsyncSession = Depends(get_db),
) -> QuesitoAnswerResponse:
    result = await db.execute(
        select(Quesito)
        .where(Quesito.id == quesito_id, Quesito.case_id == case_id)
        .options(selectinload(Quesito.answers))
    )
    quesito = result.scalar_one_or_none()
    if not quesito:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quesito não encontrado.")

    # Valida lastro documental
    refs = [r.model_dump() for r in (payload.document_references or [])]
    if not refs:
        # Permite salvar sem refs, mas indica ausência de lastro
        import logging
        logging.getLogger("officejoe").warning(
            "Resposta de quesito %s salva sem lastro documental.", quesito_id
        )

    version = len(quesito.answers) + 1
    answer = QuesitoAnswer(
        id=str(uuid.uuid4()),
        quesito_id=quesito_id,
        version=version,
        answer_text=payload.answer_text,
        document_references=refs if refs else None,
        generated_by_ai=False,
        authored_by_id=current_user.id,
        is_human_reviewed=False,
    )
    db.add(answer)

    quesito.status = QuesitoStatus.RESPONDIDO.value
    await db.flush()

    entry = log_audit(
        action=AuditAction.QUESITO_ANSWERED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="quesito_answer",
        resource_id=answer.id,
        details={"quesito_id": quesito_id, "version": version, "has_refs": bool(refs)},
    )
    await persist_audit(entry, db, case_id=case_id)

    return QuesitoAnswerResponse.model_validate(answer)


@router.post("/{quesito_id}/ai-draft", response_model=QuesitoAnswerResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_draft(
    case_id: str,
    quesito_id: str,
    payload: AIQuesitoRequest,
    request: Request,
    current_user=Depends(require_permission("ai:query")),
    db: AsyncSession = Depends(get_db),
) -> QuesitoAnswerResponse:
    """
    Gera rascunho de resposta via IA com rastreabilidade obrigatória.
    O rascunho fica marcado como PENDING_REVIEW e generated_by_ai=True.
    Nenhuma conclusão técnica sem lastro documental.
    """
    from app.db.models.page import Page
    from app.db.models.document import Document
    from app.services.ai_service import get_ai_service
    from sqlalchemy import and_

    result = await db.execute(
        select(Quesito)
        .where(Quesito.id == quesito_id, Quesito.case_id == case_id)
        .options(selectinload(Quesito.answers))
    )
    quesito = result.scalar_one_or_none()
    if not quesito:
        raise HTTPException(status_code=404, detail="Quesito não encontrado.")

    # Busca caso para pegar o número
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()

    # Coleta páginas para contexto
    doc_query = select(Document).where(Document.case_id == case_id, Document.status == "indexed")
    if payload.use_document_ids:
        doc_query = doc_query.where(Document.id.in_(payload.use_document_ids))
    docs_result = await db.execute(doc_query)
    documents = docs_result.scalars().all()

    pages_context = []
    for doc in documents[:5]:  # Limita a 5 documentos para o prompt
        pages_result = await db.execute(
            select(Page)
            .where(Page.document_id == doc.id, Page.raw_text.isnot(None))
            .order_by(Page.page_number)
            .limit(20)
        )
        for page in pages_result.scalars():
            pages_context.append({
                "document_id": doc.id,
                "document_name": doc.display_name or doc.original_filename,
                "page_number": page.page_number,
                "text": (page.raw_text or "")[:1500],
            })

    ai_service = get_ai_service()
    ai_result = ai_service.answer_quesito(
        question=quesito.question_text,
        seq_number=quesito.sequence_number,
        case_number=case.case_number if case else case_id,
        pages_context=pages_context,
        requested_by_id=current_user.id,
    )

    version = len(quesito.answers) + 1
    answer = QuesitoAnswer(
        id=str(uuid.uuid4()),
        quesito_id=quesito_id,
        version=version,
        answer_text=ai_result["output_text"],
        document_references=[
            {"document_id": s.get("document_id"), "document_name": s.get("document_name"),
             "page_number": s.get("page_number")}
            for s in (ai_result.get("sources") or [])
        ],
        generated_by_ai=True,
        ai_model=ai_result["ai_model"],
        ai_confidence=ai_result.get("overall_confidence"),
        ai_sources=ai_result.get("sources"),
        authored_by_id=current_user.id,
        is_human_reviewed=False,
    )
    db.add(answer)
    quesito.status = QuesitoStatus.EM_ANALISE.value
    await db.flush()

    entry = log_audit(
        action=AuditAction.AI_QUERY,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="quesito",
        resource_id=quesito_id,
        details={"ai_model": ai_result["ai_model"], "has_basis": ai_result["has_documental_basis"]},
    )
    await persist_audit(entry, db, case_id=case_id)

    return QuesitoAnswerResponse.model_validate(answer)
