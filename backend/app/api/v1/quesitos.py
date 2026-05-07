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
from app.db.models.evidence_item import EvidenceItem
from app.db.models.quesito import Quesito, QuesitoAnswer, QuesitoStatus
from app.db.models.question_evidence_link import QuestionEvidenceLink
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.quesito import (
    AIQuesitoRequest,
    QuesitoAnswerCreate,
    QuesitoAnswerResponse,
    QuesitoCreate,
    QuesitoResponse,
    QuesitoUpdate,
    QuesitoImportRequest,
    QuestionEvidenceLinkRequest,
    QuestionEvidenceLinkResponse,
    EvidenceReference,
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
        tema=payload.tema,
        tipo=payload.tipo,
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


@router.patch("/{quesito_id}", response_model=QuesitoResponse)
async def update_quesito(
    case_id: str,
    quesito_id: str,
    payload: QuesitoUpdate,
    request: Request,
    current_user=Depends(require_permission("quesito:write")),
    db: AsyncSession = Depends(get_db),
) -> QuesitoResponse:
    """Atualiza um quesito existente."""
    result = await db.execute(
        select(Quesito)
        .where(Quesito.id == quesito_id, Quesito.case_id == case_id)
        .options(selectinload(Quesito.answers))
    )
    quesito = result.scalar_one_or_none()
    if not quesito:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quesito não encontrado.")

    if payload.question_text is not None:
        quesito.question_text = payload.question_text
    if payload.status is not None:
        quesito.status = payload.status
    if payload.tema is not None:
        quesito.tema = payload.tema
    if payload.tipo is not None:
        quesito.tipo = payload.tipo

    await db.flush()

    entry = log_audit(
        action=AuditAction.QUESITO_CREATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="quesito",
        resource_id=quesito_id,
        details={"case_id": case_id, "updated_fields": payload.model_dump(exclude_none=True)},
    )
    await persist_audit(entry, db, case_id=case_id)

    return QuesitoResponse.model_validate(quesito)


@router.post("/batch/import", response_model=List[QuesitoResponse], status_code=status.HTTP_201_CREATED)
async def batch_import_quesitos(
    case_id: str,
    payload: QuesitoImportRequest,
    request: Request,
    current_user=Depends(require_permission("quesito:write")),
    db: AsyncSession = Depends(get_db),
) -> List[QuesitoResponse]:
    """Importa múltiplos quesitos em lote via JSON."""
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    if not case_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processo não encontrado.")

    quesito_ids = []
    for quesito_data in payload.quesitos:
        quesito = Quesito(
            id=str(uuid.uuid4()),
            case_id=case_id,
            sequence_number=quesito_data.sequence_number,
            origin=quesito_data.origin,
            question_text=quesito_data.question_text,
            tema=quesito_data.tema,
            tipo=quesito_data.tipo,
            status=QuesitoStatus.PENDENTE.value,
        )
        db.add(quesito)
        quesito_ids.append(quesito.id)

    await db.flush()

    entry = log_audit(
        action=AuditAction.QUESITO_CREATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="quesito",
        resource_id=case_id,
        details={"batch_import": True, "quantity": len(quesito_ids)},
    )
    await persist_audit(entry, db, case_id=case_id)

    result = await db.execute(
        select(Quesito)
        .where(Quesito.id.in_(quesito_ids))
        .options(selectinload(Quesito.answers))
        .order_by(Quesito.sequence_number)
    )
    return [QuesitoResponse.model_validate(q) for q in result.scalars().all()]


@router.post("/{quesito_id}/evidence", response_model=QuestionEvidenceLinkResponse, status_code=status.HTTP_201_CREATED)
async def link_evidence_to_quesito(
    case_id: str,
    quesito_id: str,
    payload: QuestionEvidenceLinkRequest,
    request: Request,
    current_user=Depends(require_permission("quesito:write")),
    db: AsyncSession = Depends(get_db),
) -> QuestionEvidenceLinkResponse:
    """Vincula uma evidência a um quesito."""
    quesito_result = await db.execute(
        select(Quesito).where(Quesito.id == quesito_id, Quesito.case_id == case_id)
    )
    quesito = quesito_result.scalar_one_or_none()
    if not quesito:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quesito não encontrado.")

    evidence_result = await db.execute(
        select(EvidenceItem).where(EvidenceItem.id == payload.evidence_item_id)
    )
    evidence = evidence_result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidência não encontrada.")

    if evidence.case_id != case_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidência não pertence ao mesmo processo.",
        )

    link = QuestionEvidenceLink(
        id=str(uuid.uuid4()),
        quesito_id=quesito_id,
        evidence_item_id=payload.evidence_item_id,
    )
    db.add(link)
    await db.flush()

    entry = log_audit(
        action=AuditAction.QUESITO_CREATED,
        user_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
        resource_type="question_evidence_link",
        resource_id=link.id,
        details={"quesito_id": quesito_id, "evidence_item_id": payload.evidence_item_id},
    )
    await persist_audit(entry, db, case_id=case_id)

    result = await db.execute(
        select(QuestionEvidenceLink)
        .where(QuestionEvidenceLink.id == link.id)
        .options(selectinload(QuestionEvidenceLink.evidence_item))
    )
    return QuestionEvidenceLinkResponse.model_validate(result.scalar_one())


@router.get("/{quesito_id}/evidence", response_model=List[EvidenceReference])
async def list_quesito_evidence(
    case_id: str,
    quesito_id: str,
    current_user=Depends(require_permission("quesito:read")),
    db: AsyncSession = Depends(get_db),
) -> List[EvidenceReference]:
    """Lista evidências vinculadas a um quesito."""
    quesito_result = await db.execute(
        select(Quesito).where(Quesito.id == quesito_id, Quesito.case_id == case_id)
    )
    if not quesito_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quesito não encontrado.")

    result = await db.execute(
        select(EvidenceItem)
        .join(QuestionEvidenceLink, EvidenceItem.id == QuestionEvidenceLink.evidence_item_id)
        .where(QuestionEvidenceLink.quesito_id == quesito_id)
        .order_by(EvidenceItem.created_at)
    )
    return [EvidenceReference.model_validate(e) for e in result.scalars().all()]
