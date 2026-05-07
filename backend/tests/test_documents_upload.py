from __future__ import annotations

import hashlib
import io

import fitz
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.file_page import FilePage
from app.db.models.page_text_block import PageTextBlock
from app.db.models.processing_job import ProcessingJob
from app.services.basic_ocr_service import BasicOCRService
from app.services.file_page_service import FilePageService
from app.services.page_preview_service import PagePreviewService


class FakeStorageService:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload_document(
        self,
        file_stream,
        object_key: str,
        file_size: int,
        content_type: str = "application/pdf",
        bucket: str | None = None,
    ) -> str:
        data = file_stream.read()
        assert len(data) == file_size
        assert content_type == "application/pdf"
        self.objects[object_key] = data
        return object_key

    def download_to_stream(self, object_key: str, bucket: str | None = None):
        data = self.objects[object_key]
        return io.BytesIO(data), len(data)

    def generate_presigned_url(
        self,
        object_key: str,
        expires_seconds: int = 3600,
        bucket: str | None = None,
    ) -> str:
        return f"https://minio.test/{object_key}?expires={expires_seconds}"


class FakeAsyncResult:
    id = "celery-task-test"


def _small_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Documento PDF pequeno para teste.")
    data = doc.tobytes()
    doc.close()
    return data


def _two_page_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page(width=200, height=300)
    doc.new_page(width=400, height=500)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.mark.asyncio
async def test_upload_pdf_stores_original_hash_metadata_and_custody_event(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    storage = FakeStorageService()
    monkeypatch.setattr(
        "app.services.document_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.create_file_pages_job.apply_async",
        lambda *args, **kwargs: FakeAsyncResult(),
    )

    pdf = _small_pdf()
    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/documents",
        files={"file": ("teste.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"category": "outro"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "teste.pdf"
    assert data["sha256_hash"] == hashlib.sha256(pdf).hexdigest()
    assert data["file_size_bytes"] == len(pdf)
    assert data["total_pages"] == 1
    assert data["pdf_is_valid"] is True
    assert data["has_native_text"] is True
    assert data["is_original_preserved"] is True
    assert data["status"] == "uploaded"
    assert data["processing_job_id"]

    result = await db_session.execute(select(Document).where(Document.id == data["id"]))
    doc = result.scalar_one()
    assert storage.objects[doc.storage_key] == pdf

    job_result = await db_session.execute(
        select(ProcessingJob).where(ProcessingJob.id == data["processing_job_id"])
    )
    job = job_result.scalar_one()
    assert job.document_id == data["id"]
    assert job.status == "queued"
    assert job.celery_task_id == "celery-task-test"

    status_response = await client.get(
        f"/api/v1/processing-jobs/{job.id}",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "queued"

    audit_result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.resource_id == data["id"],
            AuditLog.action == "document.upload",
        )
    )
    audit = audit_result.scalar_one()
    assert audit.case_id == sample_case.id
    assert audit.details["sha256"] == data["sha256_hash"]
    assert audit.details["chain_of_custody"] == "original_received_hashed_stored"


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf_mime(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "app.services.document_service.get_storage_service",
        lambda: FakeStorageService(),
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.create_file_pages_job.apply_async",
        lambda *args, **kwargs: FakeAsyncResult(),
    )

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/documents",
        files={"file": ("teste.pdf", io.BytesIO(b"not a pdf"), "text/plain")},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_file_page_service_and_endpoint_list_pdf_pages(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    storage = FakeStorageService()
    monkeypatch.setattr(
        "app.services.document_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.services.file_page_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.create_file_pages_job.apply_async",
        lambda *args, **kwargs: FakeAsyncResult(),
    )

    response = await client.post(
        f"/api/v1/cases/{sample_case.id}/documents",
        files={"file": ("duas-paginas.pdf", io.BytesIO(_two_page_pdf()), "application/pdf")},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    pages = await db_session.run_sync(
        lambda sync_session: FilePageService(sync_session).create_pages_for_file(document_id)
    )

    assert len(pages) == 2
    assert [page.page_number for page in pages] == [1, 2]
    assert pages[0].width == 200
    assert pages[0].height == 300
    assert pages[0].status_ocr == "pending"
    assert pages[0].status_preview == "pending"

    result = await db_session.execute(
        select(FilePage).where(FilePage.file_id == document_id).order_by(FilePage.page_number)
    )
    stored_pages = result.scalars().all()
    assert len(stored_pages) == 2

    list_response = await client.get(
        f"/api/v1/cases/{sample_case.id}/documents/{document_id}/file-pages",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 2
    assert data[0]["file_id"] == document_id
    assert data[0]["page_number"] == 1
    assert data[0]["status_ocr"] == "pending"
    assert data[0]["status_preview"] == "pending"


@pytest.mark.asyncio
async def test_page_preview_service_stores_png_and_endpoint_returns_url(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    storage = FakeStorageService()
    monkeypatch.setattr(
        "app.services.document_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.services.file_page_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.services.page_preview_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.api.v1.documents.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.create_file_pages_job.apply_async",
        lambda *args, **kwargs: FakeAsyncResult(),
    )

    upload_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/documents",
        files={"file": ("preview.pdf", io.BytesIO(_two_page_pdf()), "application/pdf")},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    await db_session.run_sync(
        lambda sync_session: FilePageService(sync_session).create_pages_for_file(document_id)
    )
    preview_pages = await db_session.run_sync(
        lambda sync_session: PagePreviewService(sync_session).generate_previews_for_file(
            document_id,
            batch_size=1,
        )
    )

    assert len(preview_pages) == 2
    assert all(page.status_preview == "completed" for page in preview_pages)
    assert all(page.preview_storage_key for page in preview_pages)
    assert storage.objects[preview_pages[0].preview_storage_key].startswith(b"\x89PNG")

    await db_session.flush()
    list_response = await client.get(
        f"/api/v1/cases/{sample_case.id}/documents/{document_id}/file-pages",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    file_page = list_response.json()[0]
    assert file_page["preview_storage_key"]

    url_response = await client.get(
        (
            f"/api/v1/cases/{sample_case.id}/documents/{document_id}"
            f"/file-pages/{file_page['id']}/preview-url"
        ),
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert url_response.status_code == 200
    assert url_response.json()["url"].startswith("https://minio.test/")


@pytest.mark.asyncio
async def test_basic_ocr_extracts_native_text_blocks_and_endpoint_returns_text(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    storage = FakeStorageService()
    monkeypatch.setattr(
        "app.services.document_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.services.file_page_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.services.basic_ocr_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.create_file_pages_job.apply_async",
        lambda *args, **kwargs: FakeAsyncResult(),
    )

    pdf = _small_pdf()
    upload_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/documents",
        files={"file": ("ocr-nativo.pdf", io.BytesIO(pdf), "application/pdf")},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    await db_session.run_sync(
        lambda sync_session: FilePageService(sync_session).create_pages_for_file(document_id)
    )
    processed_pages = await db_session.run_sync(
        lambda sync_session: BasicOCRService(sync_session).process_file(document_id, batch_size=1)
    )
    assert len(processed_pages) == 1
    assert processed_pages[0].status_ocr == "completed"

    blocks_result = await db_session.execute(
        select(PageTextBlock).where(PageTextBlock.file_id == document_id)
    )
    blocks = blocks_result.scalars().all()
    assert blocks
    assert any("Documento" in block.text for block in blocks)
    assert all(block.source == "native" for block in blocks)
    assert all(block.confidence == 1.0 for block in blocks)

    await db_session.flush()
    page_result = await db_session.execute(select(FilePage).where(FilePage.file_id == document_id))
    file_page = page_result.scalar_one()
    text_response = await client.get(
        (
            f"/api/v1/cases/{sample_case.id}/documents/{document_id}"
            f"/file-pages/{file_page.id}/ocr-text"
        ),
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert text_response.status_code == 200
    data = text_response.json()
    assert data["status_ocr"] == "completed"
    assert "Documento" in data["full_text"]
    assert data["blocks"]


@pytest.mark.asyncio
async def test_low_confidence_rule_marks_page_and_endpoint_lists_it(
    client: AsyncClient,
    perito_token: str,
    sample_case,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    storage = FakeStorageService()
    monkeypatch.setattr(
        "app.services.document_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.services.file_page_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.services.basic_ocr_service.get_storage_service",
        lambda: storage,
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.create_file_pages_job.apply_async",
        lambda *args, **kwargs: FakeAsyncResult(),
    )
    monkeypatch.setattr(
        "app.services.basic_ocr_service.settings.OCR_LOW_CONFIDENCE_THRESHOLD",
        0.8,
    )

    upload_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/documents",
        files={"file": ("baixa-confianca.pdf", io.BytesIO(_small_pdf()), "application/pdf")},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    await db_session.run_sync(
        lambda sync_session: FilePageService(sync_session).create_pages_for_file(document_id)
    )
    page_result = await db_session.execute(select(FilePage).where(FilePage.file_id == document_id))
    file_page = page_result.scalar_one()

    low_blocks = [
        PageTextBlock(
            file_page_id=file_page.id,
            file_id=document_id,
            page_number=file_page.page_number,
            text="texto",
            x0=0,
            y0=0,
            x1=10,
            y1=10,
            confidence=0.5,
            source="tesseract",
        ),
        PageTextBlock(
            file_page_id=file_page.id,
            file_id=document_id,
            page_number=file_page.page_number,
            text="ruidoso",
            x0=12,
            y0=0,
            x1=20,
            y1=10,
            confidence=0.7,
            source="tesseract",
        ),
    ]
    await db_session.run_sync(
        lambda sync_session: BasicOCRService(sync_session)._update_confidence_flags(
            file_page,
            low_blocks,
        )
    )
    await db_session.flush()

    assert file_page.average_confidence == pytest.approx(0.6)
    assert file_page.low_confidence is True

    response = await client.get(
        f"/api/v1/cases/{sample_case.id}/documents/{document_id}/file-pages/low-confidence",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == file_page.id
    assert data[0]["low_confidence"] is True
    assert data[0]["average_confidence"] == pytest.approx(0.6)
