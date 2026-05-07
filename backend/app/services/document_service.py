"""
Serviço de gerenciamento de documentos.
Responsável pelo upload seguro, cálculo de hash, persistência e enfileiramento OCR.
"""
from __future__ import annotations

import io
import logging
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, log_audit
from app.core.config import get_settings
from app.core.hashing import compute_sha256_stream, verify_integrity
from app.db.models.document import Document, DocumentCategory, DocumentStatus
from app.db.models.case import Case
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
        if file.content_type not in ["application/pdf", "application/octet-stream"]:
            ext = (file.filename or "").rsplit(".", 1)[-1].lower()
            if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Tipo de arquivo não permitido. Apenas: {settings.ALLOWED_UPLOAD_EXTENSIONS}",
                )

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
        2. Lê arquivo para memória (streaming seguro)
        3. Calcula SHA-256
        4. Persiste documento no banco (status=UPLOADED)
        5. Faz upload para MinIO
        6. Atualiza status para QUEUED_OCR
        7. Registra auditoria
        8. Enfileira tarefa OCR
        """
        await self._validate_upload(file)
        await self._validate_case_exists(case_id)

        # Lê o arquivo em memória (limitado pelo gateway/nginx em produção)
        content = await file.read()
        file_size = len(content)

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

        # Calcula hash SHA-256
        stream = io.BytesIO(content)
        sha256 = compute_sha256_stream(stream)
        stream.seek(0)

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
            storage_bucket=settings.MINIO_BUCKET_DOCUMENTS,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED.value,
            uploaded_by_id=uploaded_by_id,
            is_original_preserved=True,
        )
        self._db.add(doc)
        await self._db.flush()  # Persiste sem commit para obter o ID

        # Upload para MinIO (stream já na posição 0)
        try:
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

        # Verifica integridade após upload
        await self._verify_stored_integrity(doc, content)

        doc.status = DocumentStatus.QUEUED_OCR.value
        await self._db.flush()

        # Auditoria
        log_audit(
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
            },
        )

        # Enfileira OCR via Celery (import tardio para evitar circular)
        self._enqueue_ocr(document_id)

        logger.info(
            "Documento criado: id=%s case=%s sha256=%s...",
            document_id, case_id, sha256[:12],
        )
        return doc

    async def _verify_stored_integrity(self, doc: Document, original_content: bytes) -> None:
        """Verifica que o hash do conteúdo confere com o hash armazenado."""
        if not verify_integrity(original_content, doc.sha256_hash):
            doc.status = DocumentStatus.ERROR.value
            doc.error_message = "Falha de integridade: hash SHA-256 não confere."
            await self._db.flush()
            log_audit(
                action=AuditAction.DOCUMENT_INTEGRITY_FAIL,
                resource_type="document",
                resource_id=doc.id,
                details={"sha256": doc.sha256_hash},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha de integridade no documento. Upload cancelado.",
            )

    def _enqueue_ocr(self, document_id: str) -> None:
        try:
            from app.tasks.ocr_tasks import run_ocr_pipeline
            task = run_ocr_pipeline.apply_async(
                args=[document_id],
                queue="ocr",
                countdown=2,
            )
            logger.info("Tarefa OCR enfileirada: doc=%s task=%s", document_id, task.id)
        except Exception as exc:
            logger.warning("Não foi possível enfileirar OCR: %s", exc)

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
