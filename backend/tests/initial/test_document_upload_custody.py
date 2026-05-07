from __future__ import annotations

import hashlib
import io

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.processing_job import ProcessingJob
from app.services.document_service import DocumentService


@pytest.mark.asyncio
async def test_pdf_upload_hash_audit_and_chain_of_custody(
    sample_case,
    perito_user,
    db_session: AsyncSession,
    initial_pdf_bytes: bytes,
    patch_document_upload_dependencies,
):
    upload = UploadFile(
        filename="inicial.pdf",
        file=io.BytesIO(initial_pdf_bytes),
        headers={"content-type": "application/pdf"},
    )
    service = DocumentService(db_session)

    document = await service.upload_document(
        case_id=sample_case.id,
        file=upload,
        category="outro",
        display_name="PDF inicial",
        uploaded_by_id=perito_user.id,
        user_email=perito_user.email,
        ip_address="127.0.0.1",
    )

    expected_hash = hashlib.sha256(initial_pdf_bytes).hexdigest()
    assert document.original_filename == "inicial.pdf"
    assert document.display_name == "PDF inicial"
    assert document.sha256_hash == expected_hash
    assert document.file_size_bytes == len(initial_pdf_bytes)
    assert document.pdf_is_valid is True
    assert document.has_native_text is True
    assert document.is_original_preserved is True
    assert document.status == "uploaded"
    assert document.processing_job_id

    document_result = await db_session.execute(
        select(Document).where(Document.id == document.id)
    )
    stored_document = document_result.scalar_one()
    assert patch_document_upload_dependencies.objects[stored_document.storage_key] == initial_pdf_bytes

    job_result = await db_session.execute(
        select(ProcessingJob).where(ProcessingJob.id == document.processing_job_id)
    )
    job = job_result.scalar_one()
    assert job.document_id == document.id
    assert job.status == "queued"
    assert job.celery_task_id == "initial-celery-task"

    audit_result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.resource_id == document.id,
            AuditLog.action == "document.upload",
        )
    )
    audit = audit_result.scalar_one()
    assert audit.case_id == sample_case.id
    assert audit.details["sha256"] == expected_hash
    assert audit.details["storage_key"] == stored_document.storage_key
    assert audit.details["chain_of_custody"] == "original_received_hashed_stored"
