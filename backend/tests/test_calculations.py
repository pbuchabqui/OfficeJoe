from __future__ import annotations

import hashlib
import io

import pytest
from fastapi import UploadFile
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.calculation import CalculationVersion
from app.schemas.calculation import CalculationCreateRequest
from app.services.calculation_service import CalculationService


class FakeStorageService:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.buckets: dict[str, str | None] = {}

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
        assert object_key not in self.objects
        self.objects[object_key] = data
        self.buckets[object_key] = bucket
        return object_key


@pytest.mark.asyncio
async def test_calculation_service_uploads_versions_without_overwrite(
    db_session: AsyncSession,
    sample_case,
    perito_user,
    monkeypatch: pytest.MonkeyPatch,
):
    storage = FakeStorageService()
    monkeypatch.setattr(
        "app.services.calculation_service.get_storage_service",
        lambda: storage,
    )

    svc = CalculationService(db_session)
    calculation = await svc.create_calculation(
        sample_case.id,
        CalculationCreateRequest(
            calculation_type="liquidacao",
            description="Cálculo inicial de liquidação",
            responsible_user_id=perito_user.id,
        ),
    )

    first_bytes = b"versao 1"
    second_bytes = b"versao 2 revisada"
    first = await svc.upload_calculation_version(
        case_id=sample_case.id,
        calculation_id=calculation.id,
        file=_upload_file("calculo.xlsx", first_bytes),
        premises="Premissas v1",
        methodology="Metodologia v1",
        created_by_id=perito_user.id,
    )
    second = await svc.upload_calculation_version(
        case_id=sample_case.id,
        calculation_id=calculation.id,
        file=_upload_file("calculo.xlsx", second_bytes),
        premises="Premissas v2",
        methodology="Metodologia v2",
        created_by_id=perito_user.id,
    )

    assert first.version_number == 1
    assert second.version_number == 2
    assert first.storage_key != second.storage_key
    assert first.sha256_hash == hashlib.sha256(first_bytes).hexdigest()
    assert second.sha256_hash == hashlib.sha256(second_bytes).hexdigest()
    assert storage.objects[first.storage_key] == first_bytes
    assert storage.objects[second.storage_key] == second_bytes


@pytest.mark.asyncio
async def test_calculation_endpoint_creates_control_and_uploads_version(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_case,
    perito_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    storage = FakeStorageService()
    monkeypatch.setattr(
        "app.services.calculation_service.get_storage_service",
        lambda: storage,
    )

    create_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/calculations",
        json={
            "calculation_type": "liquidacao",
            "description": "Controle do cálculo pericial",
            "status": "rascunho",
        },
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert create_response.status_code == 201
    calculation_id = create_response.json()["id"]

    file_bytes = b"planilha simulada"
    upload_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/calculations/{calculation_id}/versions",
        files={
            "file": (
                "calculo.xlsx",
                io.BytesIO(file_bytes),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"premises": "Premissas testadas", "methodology": "Metodologia declarada"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert upload_response.status_code == 201
    data = upload_response.json()
    assert data["calculation_id"] == calculation_id
    assert data["version_number"] == 1
    assert data["original_filename"] == "calculo.xlsx"
    assert data["sha256_hash"] == hashlib.sha256(file_bytes).hexdigest()
    assert data["premises"] == "Premissas testadas"
    assert data["methodology"] == "Metodologia declarada"
    assert storage.objects[data["storage_key"]] == file_bytes

    result = await db_session.execute(
        select(CalculationVersion).where(CalculationVersion.calculation_id == calculation_id)
    )
    versions = result.scalars().all()
    assert len(versions) == 1
    assert versions[0].storage_key == data["storage_key"]


def _upload_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    )
