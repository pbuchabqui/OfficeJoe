"""
Endpoints de documentos: upload, listagem, download, verificação de integridade.
O arquivo original NUNCA é modificado após o upload.
"""
from __future__ import annotations

import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, persist_audit, require_permission
from app.core.audit import AuditAction, log_audit
from app.db.models.document import Document
from app.db.models.file_page import FilePage, FilePageInitialStatus
from app.db.models.page_classification import PageClassification
from app.db.models.page_text_block import PageTextBlock
from app.db.models.page import Page
from app.db.models.extraction import Extraction
from app.db.models.processing_job import ProcessingJob, ProcessingJobStatus
from app.db.session import get_db
from app.schemas.document import (
    DocumentAnalysisSnippetResponse,
    DocumentAnalysisSummaryResponse,
    DocumentAnalysisTermResponse,
    DocumentIntegrityResponse,
    DocumentPericialAnalysisResponse,
    DocumentProcessingProgressResponse,
    DocumentResponse,
    ExtractionResponse,
    PageResponse,
)
from app.schemas.file_page import FilePagePreviewUrlResponse, FilePageResponse
from app.schemas.page_text_block import FilePageOCRTextResponse, PageTextBlockResponse
from app.schemas.page_classification import PageClassificationCorrectionRequest, PageClassificationResponse
from app.services.document_service import DocumentService
from app.services.inventory_service import generate_inventory, list_inventory, update_inventory_item
from app.services.page_classification_service import PageClassificationService, get_page_classification_provider
from app.services.storage_service import get_storage_service
from app.schemas.inventory import InventoryItemResponse, InventoryResponse, InventoryItemUpdateRequest

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["Documentos"])

_STOPWORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos", "e", "em",
    "na", "nas", "no", "nos", "o", "os", "ou", "para", "por", "que", "se", "um", "uma",
    "uns", "umas", "não", "sim", "sua", "seu", "suas", "seus", "mais", "menos", "pela",
    "pelo", "pelas", "pelos", "processo", "página", "pagina", "documento",
}


def _processing_progress_payload(
    document: Document,
    file_pages: list[FilePage],
    job: ProcessingJob | None,
) -> DocumentProcessingProgressResponse:
    now = datetime.now(timezone.utc)
    created_at = document.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    pages_total = document.total_pages or len(file_pages)
    pages_registered = len(file_pages)
    previews_completed = sum(
        1 for page in file_pages if page.status_preview == FilePageInitialStatus.COMPLETED.value
    )
    ocr_completed = sum(
        1 for page in file_pages if page.status_ocr == FilePageInitialStatus.COMPLETED.value
    )
    failed_pages = sum(
        1
        for page in file_pages
        if page.status_preview == FilePageInitialStatus.FAILED.value
        or page.status_ocr == FilePageInitialStatus.FAILED.value
    )

    if pages_total <= 0:
        registration_ratio = 0.0
        preview_ratio = 0.0
        ocr_ratio = 0.0
    else:
        registration_ratio = min(pages_registered / pages_total, 1.0)
        preview_ratio = min(previews_completed / pages_total, 1.0)
        ocr_ratio = min(ocr_completed / pages_total, 1.0)

    progress_percent = round(
        10
        + (15 * registration_ratio)
        + (30 * preview_ratio)
        + (45 * ocr_ratio)
    )

    status = "processing"
    active_stage = "Registrando páginas"
    if document.error_message or document.status == "error" or job and job.status == ProcessingJobStatus.FAILED.value:
        status = "failed"
        active_stage = "Falha no processamento"
    elif pages_total > 0 and pages_registered >= pages_total and previews_completed >= pages_total and ocr_completed >= pages_total:
        status = "completed"
        active_stage = "Concluído"
        progress_percent = 100
    elif pages_registered < pages_total:
        active_stage = "Registrando páginas"
    elif previews_completed < pages_total:
        active_stage = "Gerando visualizações"
    elif ocr_completed < pages_total:
        active_stage = "Extraindo texto por OCR"

    progress_percent = max(0, min(progress_percent, 100))
    elapsed_seconds = max(0, int((now - created_at).total_seconds()))
    estimated_remaining_seconds: int | None = None
    if status == "processing" and 0 < progress_percent < 100 and elapsed_seconds > 0:
        estimated_remaining_seconds = round(elapsed_seconds * ((100 - progress_percent) / progress_percent))

    return DocumentProcessingProgressResponse(
        document_id=document.id,
        case_id=document.case_id,
        status=status,
        active_stage=active_stage,
        progress_percent=progress_percent,
        pages_total=pages_total,
        pages_registered=pages_registered,
        previews_completed=previews_completed,
        ocr_completed=ocr_completed,
        failed_pages=failed_pages,
        elapsed_seconds=elapsed_seconds,
        estimated_remaining_seconds=estimated_remaining_seconds,
        processing_job_id=job.id if job else None,
        job_status=job.status if job else None,
        updated_at=now,
    )


def _normalize_summary_text(text: str) -> str:
    return " ".join(text.split())


def _top_terms(text: str) -> list[DocumentAnalysisTermResponse]:
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", text.lower())
    counter = Counter(word for word in words if word not in _STOPWORDS)
    return [
        DocumentAnalysisTermResponse(term=term, count=count)
        for term, count in counter.most_common(10)
    ]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    category: str = Form(default="outro"),
    display_name: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    current_user=Depends(require_permission("document:write")),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    svc = DocumentService(db)
    doc = await svc.upload_document(
        case_id=case_id,
        file=file,
        category=category,
        display_name=display_name,
        description=description,
        uploaded_by_id=current_user.id,
        user_email=current_user.email,
        ip_address=get_client_ip(request),
    )
    return DocumentResponse.model_validate(doc)


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    case_id: str,
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    q = select(Document).where(Document.case_id == case_id)
    if status:
        q = q.where(Document.status == status)
    if category:
        q = q.where(Document.category == category)
    q = q.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    case_id: str,
    document_id: str,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.case_id == case_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/integrity", response_model=DocumentIntegrityResponse)
async def check_integrity(
    case_id: str,
    document_id: str,
    request: Request,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> DocumentIntegrityResponse:
    """Verifica integridade SHA-256 sem modificar o arquivo."""
    svc = DocumentService(db)
    result = await svc.check_integrity(
        document_id=document_id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
    )
    return DocumentIntegrityResponse(**result)


@router.get("/{document_id}/processing-progress", response_model=DocumentProcessingProgressResponse)
async def get_document_processing_progress(
    case_id: str,
    document_id: str,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> DocumentProcessingProgressResponse:
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.case_id == case_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    pages_result = await db.execute(
        select(FilePage).where(FilePage.file_id == document_id).order_by(FilePage.page_number)
    )
    job_result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id, ProcessingJob.case_id == case_id)
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )
    return _processing_progress_payload(
        document=document,
        file_pages=list(pages_result.scalars().all()),
        job=job_result.scalar_one_or_none(),
    )


@router.get("/{document_id}/analysis-summary", response_model=DocumentAnalysisSummaryResponse)
async def get_document_analysis_summary(
    case_id: str,
    document_id: str,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> DocumentAnalysisSummaryResponse:
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.case_id == case_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    stats_result = await db.execute(
        select(
            func.count(PageTextBlock.id),
            func.count(distinct(PageTextBlock.page_number)),
            func.coalesce(func.sum(func.length(PageTextBlock.text)), 0),
        ).where(PageTextBlock.file_id == document_id)
    )
    text_blocks, pages_with_text, extracted_text_chars = stats_result.one()

    blocks_result = await db.execute(
        select(PageTextBlock)
        .where(PageTextBlock.file_id == document_id)
        .order_by(PageTextBlock.page_number, PageTextBlock.y0, PageTextBlock.x0)
        .limit(3000)
    )
    page_texts: dict[int, list[str]] = defaultdict(list)
    all_text_parts: list[str] = []
    for block in blocks_result.scalars().all():
        clean_text = _normalize_summary_text(block.text)
        if not clean_text:
            continue
        page_texts[block.page_number].append(clean_text)
        all_text_parts.append(clean_text)

    snippets = []
    for page_number in sorted(page_texts)[:5]:
        page_text = _normalize_summary_text(" ".join(page_texts[page_number]))
        snippets.append(
            DocumentAnalysisSnippetResponse(
                page_number=page_number,
                text=page_text[:700],
            )
        )

    status_value = "ready" if text_blocks else "empty"
    full_text_sample = " ".join(all_text_parts)[:40000]
    return DocumentAnalysisSummaryResponse(
        document_id=document_id,
        case_id=case_id,
        status=status_value,
        pages_total=document.total_pages or 0,
        pages_with_text=int(pages_with_text or 0),
        text_blocks=int(text_blocks or 0),
        extracted_text_chars=int(extracted_text_chars or 0),
        top_terms=_top_terms(full_text_sample),
        snippets=snippets,
    )


@router.post("/{document_id}/pericial-analysis", response_model=DocumentPericialAnalysisResponse)
async def run_document_pericial_analysis(
    case_id: str,
    document_id: str,
    current_user=Depends(require_permission("document:write")),
    db: AsyncSession = Depends(get_db),
) -> DocumentPericialAnalysisResponse:
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.case_id == case_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    pages_result = await db.execute(
        select(FilePage).where(FilePage.file_id == document_id).order_by(FilePage.page_number)
    )
    file_pages = list(pages_result.scalars().all())
    if not file_pages:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O processamento técnico ainda não registrou as páginas do PDF.",
        )

    text_result = await db.execute(
        select(PageTextBlock.file_page_id, PageTextBlock.text)
        .where(PageTextBlock.file_id == document_id)
        .order_by(PageTextBlock.page_number, PageTextBlock.y0, PageTextBlock.x0)
    )
    text_by_page: dict[str, list[str]] = defaultdict(list)
    for file_page_id, text_value in text_result.all():
        if text_value:
            text_by_page[file_page_id].append(text_value)

    existing_result = await db.execute(
        select(PageClassification).where(PageClassification.file_id == document_id)
    )
    classifications_by_page = {
        classification.file_page_id: classification
        for classification in existing_result.scalars().all()
    }

    provider = get_page_classification_provider()
    for file_page in file_pages:
        page_text = _normalize_summary_text(" ".join(text_by_page.get(file_page.id, [])))[:12000]
        ai_response = await provider.classify_page(page_text)
        classification = classifications_by_page.get(file_page.id)
        if not classification:
            classification = PageClassification(
                id=str(uuid.uuid4()),
                file_page_id=file_page.id,
                file_id=file_page.file_id,
                page_number=file_page.page_number,
            )
            db.add(classification)

        classification.document_class = ai_response.document_class
        classification.confidence = ai_response.confidence
        classification.rationale = ai_response.rationale
        classification.provider = provider.provider_name
        classification.model_name = provider.model_name
        classification.raw_response = ai_response.model_dump()

    await db.flush()
    inventory_items = await generate_inventory(db, document_id)
    inventory = InventoryResponse(
        document_id=document_id,
        total_groups=len(inventory_items),
        items=[InventoryItemResponse.model_validate(item) for item in inventory_items],
    )
    return DocumentPericialAnalysisResponse(
        document_id=document_id,
        case_id=case_id,
        status="completed",
        pages_total=len(file_pages),
        pages_classified=len(file_pages),
        inventory=inventory,
        message="Classificação documental e inventário dos autos concluídos.",
    )


@router.get("/{document_id}/download-url")
async def get_download_url(
    case_id: str,
    document_id: str,
    expires_seconds: int = Query(3600, le=86400),
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Gera URL pré-assinada para download temporário (sem expor chave de armazenamento)."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.case_id == case_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    storage = get_storage_service()
    url = storage.generate_presigned_url(
        object_key=doc.storage_key,
        expires_seconds=expires_seconds,
    )
    return {
        "url": url,
        "expires_in": expires_seconds,
        "filename": doc.original_filename,
        "sha256_hash": doc.sha256_hash,
    }


@router.get("/{document_id}/pages", response_model=List[PageResponse])
async def list_pages(
    case_id: str,
    document_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> List[PageResponse]:
    result = await db.execute(
        select(Page)
        .where(Page.document_id == document_id)
        .order_by(Page.page_number)
        .offset(skip)
        .limit(limit)
    )
    pages = result.scalars().all()
    return [PageResponse.model_validate(p) for p in pages]


@router.get("/{document_id}/file-pages", response_model=List[FilePageResponse])
async def list_file_pages(
    case_id: str,
    document_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> List[FilePageResponse]:
    doc_result = await db.execute(
        select(Document.id).where(Document.id == document_id, Document.case_id == case_id)
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    result = await db.execute(
        select(FilePage)
        .where(FilePage.file_id == document_id)
        .order_by(FilePage.page_number)
        .offset(skip)
        .limit(limit)
    )
    return [FilePageResponse.model_validate(page) for page in result.scalars().all()]


@router.get("/{document_id}/file-pages/low-confidence", response_model=List[FilePageResponse])
async def list_low_confidence_file_pages(
    case_id: str,
    document_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> List[FilePageResponse]:
    doc_result = await db.execute(
        select(Document.id).where(Document.id == document_id, Document.case_id == case_id)
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    result = await db.execute(
        select(FilePage)
        .where(FilePage.file_id == document_id, FilePage.low_confidence.is_(True))
        .order_by(FilePage.page_number)
        .offset(skip)
        .limit(limit)
    )
    return [FilePageResponse.model_validate(page) for page in result.scalars().all()]


@router.get(
    "/{document_id}/file-pages/{file_page_id}/preview-url",
    response_model=FilePagePreviewUrlResponse,
)
async def get_file_page_preview_url(
    case_id: str,
    document_id: str,
    file_page_id: str,
    expires_seconds: int = Query(3600, le=86400),
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> FilePagePreviewUrlResponse:
    result = await db.execute(
        select(FilePage, Document)
        .join(Document, Document.id == FilePage.file_id)
        .where(
            FilePage.id == file_page_id,
            FilePage.file_id == document_id,
            Document.case_id == case_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Página não encontrada.")

    file_page, document = row
    if not file_page.preview_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview não encontrado.")

    storage = get_storage_service()
    url = storage.generate_presigned_url(
        object_key=file_page.preview_storage_key,
        expires_seconds=expires_seconds,
        bucket=document.storage_bucket,
    )
    return FilePagePreviewUrlResponse(
        url=url,
        expires_in=expires_seconds,
        file_page_id=file_page.id,
        file_id=file_page.file_id,
        page_number=file_page.page_number,
    )


@router.get(
    "/{document_id}/file-pages/{file_page_id}/ocr-text",
    response_model=FilePageOCRTextResponse,
)
async def get_file_page_ocr_text(
    case_id: str,
    document_id: str,
    file_page_id: str,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> FilePageOCRTextResponse:
    page_result = await db.execute(
        select(FilePage, Document)
        .join(Document, Document.id == FilePage.file_id)
        .where(
            FilePage.id == file_page_id,
            FilePage.file_id == document_id,
            Document.case_id == case_id,
        )
    )
    row = page_result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Página não encontrada.")

    file_page, _document = row
    blocks_result = await db.execute(
        select(PageTextBlock)
        .where(PageTextBlock.file_page_id == file_page_id)
        .order_by(PageTextBlock.y0, PageTextBlock.x0)
    )
    blocks = blocks_result.scalars().all()
    return FilePageOCRTextResponse(
        file_page_id=file_page.id,
        file_id=file_page.file_id,
        page_number=file_page.page_number,
        status_ocr=file_page.status_ocr,
        full_text=" ".join(block.text for block in blocks),
        blocks=[PageTextBlockResponse.model_validate(block) for block in blocks],
    )


@router.post(
    "/{document_id}/file-pages/{file_page_id}/classification",
    response_model=PageClassificationResponse,
)
async def classify_file_page(
    case_id: str,
    document_id: str,
    file_page_id: str,
    current_user=Depends(require_permission("document:write")),
    db: AsyncSession = Depends(get_db),
) -> PageClassificationResponse:
    service = PageClassificationService(db)
    try:
        classification = await service.classify_page(
            case_id=case_id,
            document_id=document_id,
            file_page_id=file_page_id,
        )
    except ValueError as exc:
        detail = str(exc)
        if "não encontrada" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
    return PageClassificationResponse.model_validate(classification)


@router.get(
    "/{document_id}/file-pages/{file_page_id}/classification",
    response_model=PageClassificationResponse,
)
async def get_file_page_classification(
    case_id: str,
    document_id: str,
    file_page_id: str,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> PageClassificationResponse:
    service = PageClassificationService(db)
    try:
        classification = await service.get_classification(
            case_id=case_id,
            document_id=document_id,
            file_page_id=file_page_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if not classification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classificação não encontrada.")
    return PageClassificationResponse.model_validate(classification)


@router.post(
    "/{document_id}/file-pages/{file_page_id}/classification/approve",
    response_model=PageClassificationResponse,
)
async def approve_file_page_classification(
    case_id: str,
    document_id: str,
    file_page_id: str,
    request: Request,
    current_user=Depends(require_permission("document:write")),
    db: AsyncSession = Depends(get_db),
) -> PageClassificationResponse:
    service = PageClassificationService(db)
    try:
        classification = await service.approve_classification(
            case_id=case_id,
            document_id=document_id,
            file_page_id=file_page_id,
            validated_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    entry = log_audit(
        action=AuditAction.DOCUMENT_CLASSIFICATION_APPROVED,
        user_id=current_user.id,
        user_email=current_user.email,
        resource_type="page_classification",
        resource_id=classification.id,
        ip_address=get_client_ip(request),
        details={
            "case_id": case_id,
            "document_id": document_id,
            "file_page_id": file_page_id,
            "document_class": classification.document_class,
        },
    )
    await persist_audit(entry, db, case_id=case_id)
    return PageClassificationResponse.model_validate(classification)


@router.patch(
    "/{document_id}/file-pages/{file_page_id}/classification",
    response_model=PageClassificationResponse,
)
async def correct_file_page_classification(
    case_id: str,
    document_id: str,
    file_page_id: str,
    payload: PageClassificationCorrectionRequest,
    request: Request,
    current_user=Depends(require_permission("document:write")),
    db: AsyncSession = Depends(get_db),
) -> PageClassificationResponse:
    service = PageClassificationService(db)
    try:
        classification = await service.correct_classification(
            case_id=case_id,
            document_id=document_id,
            file_page_id=file_page_id,
            document_class=payload.document_class,
            validated_by=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        if "inválida" in detail:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    entry = log_audit(
        action=AuditAction.DOCUMENT_CLASSIFICATION_CORRECTED,
        user_id=current_user.id,
        user_email=current_user.email,
        resource_type="page_classification",
        resource_id=classification.id,
        ip_address=get_client_ip(request),
        details={
            "case_id": case_id,
            "document_id": document_id,
            "file_page_id": file_page_id,
            "document_class": classification.document_class,
        },
    )
    await persist_audit(entry, db, case_id=case_id)
    return PageClassificationResponse.model_validate(classification)


@router.get("/{document_id}/extractions", response_model=List[ExtractionResponse])
async def list_extractions(
    case_id: str,
    document_id: str,
    extraction_type: Optional[str] = Query(None),
    page_number: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, le=1000),
    current_user=Depends(require_permission("extraction:read")),
    db: AsyncSession = Depends(get_db),
) -> List[ExtractionResponse]:
    q = select(Extraction).where(Extraction.document_id == document_id)
    if extraction_type:
        q = q.where(Extraction.extraction_type == extraction_type)
    if page_number:
        q = q.where(Extraction.page_number == page_number)
    q = q.order_by(Extraction.page_number).offset(skip).limit(limit)
    result = await db.execute(q)
    return [ExtractionResponse.model_validate(e) for e in result.scalars().all()]


# ── Inventário automático dos autos ──────────────────────────────────────────

@router.post(
    "/{document_id}/inventory",
    response_model=InventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar inventário automático",
)
async def generate_document_inventory(
    case_id: str,
    document_id: str,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> InventoryResponse:
    """
    Agrupa páginas consecutivas com a mesma classe documental e persiste o inventário.
    Substitui completamente qualquer inventário anterior do documento.
    Requer que o documento tenha classificações de página geradas.
    """
    doc = await db.get(Document, document_id)
    if doc is None or doc.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    items = await generate_inventory(db, document_id)
    return InventoryResponse(
        document_id=document_id,
        total_groups=len(items),
        items=[InventoryItemResponse.model_validate(i) for i in items],
    )


@router.get(
    "/{document_id}/inventory",
    response_model=InventoryResponse,
    summary="Listar inventário do documento",
)
async def get_document_inventory(
    case_id: str,
    document_id: str,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> InventoryResponse:
    """
    Retorna o inventário atual do documento, ordenado por página inicial.
    Retorna lista vazia se o inventário ainda não foi gerado.
    """
    doc = await db.get(Document, document_id)
    if doc is None or doc.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    items = await list_inventory(db, document_id)
    return InventoryResponse(
        document_id=document_id,
        total_groups=len(items),
        items=[InventoryItemResponse.model_validate(i) for i in items],
    )


@router.patch(
    "/{document_id}/inventory/{item_id}",
    response_model=InventoryItemResponse,
    summary="Editar item de inventário",
)
async def update_inventory_item_endpoint(
    case_id: str,
    document_id: str,
    item_id: str,
    payload: InventoryItemUpdateRequest,
    request: Request,
    current_user=Depends(require_permission("document:write")),
    db: AsyncSession = Depends(get_db),
) -> InventoryItemResponse:
    """
    Edita um item de inventário: rename, alterar classe/páginas, marcar relevância.
    Registra mudanças em auditoria. Valida start_page <= end_page.
    """
    from app.db.models.document_inventory_item import DocumentInventoryItem

    doc = await db.get(Document, document_id)
    if doc is None or doc.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")

    item = await db.get(DocumentInventoryItem, item_id)
    if item is None or item.document_id != document_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de inventário não encontrado.")

    if not payload.has_changes():
        return InventoryItemResponse.model_validate(item)

    try:
        await update_inventory_item(
            db,
            item,
            custom_label=payload.custom_label,
            document_class=payload.document_class,
            start_page=payload.start_page,
            end_page=payload.end_page,
            is_relevant=payload.is_relevant,
            user_id=current_user.id,
            user_email=current_user.email,
            ip_address=get_client_ip(request),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return InventoryItemResponse.model_validate(item)
