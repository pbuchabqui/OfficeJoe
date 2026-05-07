"""
Endpoints de documentos: upload, listagem, download, verificação de integridade.
O arquivo original NUNCA é modificado após o upload.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_user, persist_audit, require_permission
from app.core.audit import AuditAction, log_audit
from app.db.models.document import Document
from app.db.models.file_page import FilePage
from app.db.models.page_text_block import PageTextBlock
from app.db.models.page import Page
from app.db.models.extraction import Extraction
from app.db.session import get_db
from app.schemas.document import DocumentIntegrityResponse, DocumentResponse, ExtractionResponse, PageResponse
from app.schemas.file_page import FilePagePreviewUrlResponse, FilePageResponse
from app.schemas.page_text_block import FilePageOCRTextResponse, PageTextBlockResponse
from app.schemas.page_classification import PageClassificationCorrectionRequest, PageClassificationResponse
from app.services.document_service import DocumentService
from app.services.page_classification_service import PageClassificationService
from app.services.storage_service import get_storage_service

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["Documentos"])


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
