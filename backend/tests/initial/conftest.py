from __future__ import annotations

import io

import fitz
import pytest


class InitialFakeStorageService:
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
        return f"https://storage.test/{object_key}?expires={expires_seconds}"


class InitialFakeAsyncResult:
    id = "initial-celery-task"


@pytest.fixture
def initial_storage() -> InitialFakeStorageService:
    return InitialFakeStorageService()


@pytest.fixture
def initial_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "PDF inicial para testes automatizados.")
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def patch_document_upload_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    initial_storage: InitialFakeStorageService,
) -> InitialFakeStorageService:
    monkeypatch.setattr(
        "app.services.document_service.get_storage_service",
        lambda: initial_storage,
    )
    monkeypatch.setattr(
        "app.tasks.processing_tasks.create_file_pages_job.apply_async",
        lambda *args, **kwargs: InitialFakeAsyncResult(),
    )
    return initial_storage
