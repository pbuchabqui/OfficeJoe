"""
Serviço de gerenciamento de documentos.
Responsável pelo upload seguro, cálculo de hash e persistência.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, AuditEntry, log_audit
from app.core.config import get_settings
from app.core.hashing import compute_sha256_stream, verify_integrity
from app.db.models.audit_log import AuditLog
from app.db.models.document import Document, DocumentCategory, DocumentStatus
from app.db.models.case import Case
from app.db.models.processing_job import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.services.pdf_metadata_service import extract_pdf_metadata
from app.services.storage_service import get_storage_service

logger = logging.getLogger("officejoe.document_service")
settings = get_settings()


class DocumentService:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._storage = get_storage_service()

    def _build_storage_key(self, case_id: str, document_id: str, filename: str) -> str:
        """Chave de armazenamento hierárquica e imutável."""
        safe_name = filename.replace(" ", "_").replace("/", "_")
        return f"cases/{case_id}/documents/{document_id}/{safe_name}"

    async def _validate_case_exists(self, case_id: str) -> Case:
        result = await self._db.execute(select(Case).where(Case.id == case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processo {case_id} não encontrado.",
            )
        return case

    async def _validate_upload(self, file: UploadFile) -> None:
        ext = Path(file.filename or "").suffix.lower().lstrip(".")
        if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Extensão não permitida. Apenas: {settings.ALLOWED_UPLOAD_EXTENSIONS}",
            )
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="MIME type não permitido. Apenas application/pdf.",
            )

    def _get_upload_size(self, file: UploadFile) -> int:
        stream = file.file
        pos = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(pos)
        return size

    async def upload_document(
        self,
        case_id: str,
        file: UploadFile,
        category: str = DocumentCategory.OUTRO.value,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        uploaded_by_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Document:
        """
        Fluxo completo de upload:
        1. Valida tipo/tamanho
        2. Calcula tamanho e SHA-256 por stream
        3. Extrai metadados iniciais sem alterar o original
        4. Persiste documento no banco (status=UPLOADED)
        5. Faz upload para MinIO
        6. Registra evento de cadeia de custódia
        """
        await self._validate_upload(file)
        await self._validate_case_exists(case_id)

        stream = file.file
        file_size = self._get_upload_size(file)

        if file_size > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo excede o limite de {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo vazio não é permitido.",
            )

        stream.seek(0)
        sha256 = compute_sha256_stream(stream)
        metadata = extract_pdf_metadata(stream, file_size)

        document_id = str(uuid.uuid4())
        original_filename = file.filename or "documento.pdf"
        storage_key = self._build_storage_key(case_id, document_id, original_filename)

        # Cria registro no banco
        doc = Document(
            id=document_id,
            case_id=case_id,
            original_filename=original_filename,
            display_name=display_name or original_filename,
            category=category,
            description=description,
            sha256_hash=sha256,
            file_size_bytes=file_size,
            mime_type=file.content_type or "application/pdf",
            total_pages=metadata.total_pages,
            pdf_is_valid=metadata.pdf_is_valid,
            has_native_text=metadata.has_native_text,
            storage_bucket=settings.MINIO_BUCKET_DOCUMENTS,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED.value,
            uploaded_by_id=uploaded_by_id,
            is_original_preserved=True,
        )
        self._db.add(doc)
        await self._db.flush()  # Persiste sem commit para obter o ID

        # Upload para MinIO sem modificar o arquivo original.
        try:
            stream.seek(0)
            self._storage.upload_document(
                file_stream=stream,
                object_key=storage_key,
                file_size=file_size,
                content_type=file.content_type or "application/pdf",
            )
        except Exception as exc:
            logger.error("Falha no upload para MinIO: doc_id=%s erro=%s", document_id, exc)
            doc.status = DocumentStatus.ERROR.value
            doc.error_message = str(exc)
            await self._db.flush()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao armazenar o documento. Tente novamente.",
            )

        entry = log_audit(
            action=AuditAction.DOCUMENT_UPLOAD,
            user_id=uploaded_by_id,
            user_email=user_email,
            resource_type="document",
            resource_id=document_id,
            ip_address=ip_address,
            details={
                "case_id": case_id,
                "filename": original_filename,
                "sha256": sha256,
                "size_bytes": file_size,
                "category": category,
                "storage_bucket": settings.MINIO_BUCKET_DOCUMENTS,
                "storage_key": storage_key,
                "pdf_is_valid": metadata.pdf_is_valid,
                "total_pages": metadata.total_pages,
                "has_native_text": metadata.has_native_text,
                "chain_of_custody": "original_received_hashed_stored",
            },
        )
        await self._persist_custody_event(entry, case_id)
        processing_job = await self._enqueue_page_registration_job(
            document_id=document_id,
            case_id=case_id,
            created_by_id=uploaded_by_id,
        )
        setattr(doc, "processing_job_id", processing_job.id)

        logger.info(
            "Documento criado: id=%s case=%s sha256=%s...",
            document_id, case_id, sha256[:12],
        )
        return doc

    async def _persist_custody_event(self, entry: AuditEntry, case_id: str) -> None:
        log = AuditLog(
            id=entry.id,
            timestamp=entry.timestamp,
            action=entry.action.value,
            success=entry.success,
            user_id=entry.user_id,
            user_email=entry.user_email,
            ip_address=entry.ip_address,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            case_id=case_id,
            details=entry.details,
        )
        self._db.add(log)
        await self._db.flush()

    async def _enqueue_page_registration_job(
        self,
        document_id: str,
        case_id: str,
        created_by_id: Optional[str],
    ) -> ProcessingJob:
        job = ProcessingJob(
            id=str(uuid.uuid4()),
            document_id=document_id,
            case_id=case_id,
            job_type=ProcessingJobType.FILE_PAGE_REGISTRATION.value,
            status=ProcessingJobStatus.QUEUED.value,
            created_by_id=created_by_id,
        )
        self._db.add(job)
        await self._db.flush()
        await self._db.commit()

        try:
            from app.tasks.processing_tasks import create_file_pages_job
            task = create_file_pages_job.apply_async(args=[job.id], queue="processing")
            job.celery_task_id = task.id
            await self._db.commit()
        except Exception as exc:
            logger.warning("Não foi possível enfileirar job básico: job=%s erro=%s", job.id, exc)
            job.status = ProcessingJobStatus.FAILED.value
            job.error_message = "Falha ao enfileirar task Celery."
            await self._db.commit()
        return job

    async def check_integrity(
        self,
        document_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        """
        Baixa o arquivo do storage e verifica a integridade SHA-256.
        Retorna status de integridade sem modificar o arquivo.
        """
        result = await self._db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Documento não encontrado.")

        try:
            stream, _ = self._storage.download_to_stream(doc.storage_key)
            ok = verify_integrity(stream, doc.sha256_hash)
        except Exception as exc:
            ok = False
            logger.error("Erro na verificação de integridade: %s", exc)

        action = AuditAction.DOCUMENT_INTEGRITY_CHECK if ok else AuditAction.DOCUMENT_INTEGRITY_FAIL
        log_audit(
            action=action,
            user_id=user_id,
            resource_type="document",
            resource_id=document_id,
            ip_address=ip_address,
            details={"stored_hash": doc.sha256_hash, "integrity_ok": ok},
            success=ok,
        )
        return {
            "document_id": document_id,
            "sha256_hash": doc.sha256_hash,
            "integrity_ok": ok,
            "filename": doc.original_filename,
        }
