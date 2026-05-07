"""Service for calculation control and immutable file version uploads."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.hashing import compute_sha256_stream
from app.db.models.calculation import Calculation, CalculationVersion
from app.db.models.case import Case
from app.db.models.user import User
from app.schemas.calculation import CalculationCreateRequest
from app.services.storage_service import get_storage_service

logger = logging.getLogger("officejoe.calculation_service")
settings = get_settings()


class CalculationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._storage = get_storage_service()

    async def create_calculation(
        self,
        case_id: str,
        payload: CalculationCreateRequest,
    ) -> Calculation:
        await self._validate_case_exists(case_id)
        if payload.responsible_user_id:
            await self._validate_user_exists(payload.responsible_user_id)

        calculation = Calculation(
            id=str(uuid.uuid4()),
            case_id=case_id,
            calculation_type=payload.calculation_type,
            description=payload.description,
            responsible_user_id=payload.responsible_user_id,
            status=payload.status,
        )
        self._db.add(calculation)
        await self._db.flush()
        return calculation

    async def upload_calculation_version(
        self,
        case_id: str,
        calculation_id: str,
        file: UploadFile,
        premises: str | None,
        methodology: str | None,
        created_by_id: str | None,
    ) -> CalculationVersion:
        calculation = await self._get_calculation(case_id, calculation_id)
        file_size = _get_upload_size(file)
        if file_size <= 0:
            raise ValueError("Arquivo de cálculo vazio não é permitido.")

        stream = file.file
        stream.seek(0)
        sha256 = compute_sha256_stream(stream)

        next_version = await self._next_version_number(calculation_id)
        version_id = str(uuid.uuid4())
        original_filename = file.filename or "calculo"
        storage_key = self._build_storage_key(
            case_id=case_id,
            calculation_id=calculation.id,
            version_id=version_id,
            version_number=next_version,
            filename=original_filename,
        )
        content_type = file.content_type or "application/octet-stream"

        version = CalculationVersion(
            id=version_id,
            calculation_id=calculation.id,
            version_number=next_version,
            original_filename=original_filename,
            storage_bucket=settings.MINIO_BUCKET_EXPORTS,
            storage_key=storage_key,
            sha256_hash=sha256,
            file_size_bytes=file_size,
            mime_type=content_type,
            premises=premises,
            methodology=methodology,
            created_by_id=created_by_id,
        )
        self._db.add(version)
        await self._db.flush()

        try:
            stream.seek(0)
            self._storage.upload_document(
                file_stream=stream,
                object_key=storage_key,
                file_size=file_size,
                content_type=content_type,
                bucket=settings.MINIO_BUCKET_EXPORTS,
            )
        except Exception:
            logger.exception("Falha no upload da versão de cálculo: calculation=%s", calculation_id)
            raise

        return version

    async def _validate_case_exists(self, case_id: str) -> Case:
        case = await self._db.get(Case, case_id)
        if not case:
            raise ValueError(f"Processo {case_id} não encontrado.")
        return case

    async def _validate_user_exists(self, user_id: str) -> User:
        user = await self._db.get(User, user_id)
        if not user:
            raise ValueError(f"Usuário responsável {user_id} não encontrado.")
        return user

    async def _get_calculation(self, case_id: str, calculation_id: str) -> Calculation:
        result = await self._db.execute(
            select(Calculation).where(
                Calculation.id == calculation_id,
                Calculation.case_id == case_id,
            )
        )
        calculation = result.scalar_one_or_none()
        if not calculation:
            raise ValueError(f"Cálculo {calculation_id} não encontrado.")
        return calculation

    async def _next_version_number(self, calculation_id: str) -> int:
        current = await self._db.scalar(
            select(func.max(CalculationVersion.version_number)).where(
                CalculationVersion.calculation_id == calculation_id,
            )
        )
        return int(current or 0) + 1

    def _build_storage_key(
        self,
        case_id: str,
        calculation_id: str,
        version_id: str,
        version_number: int,
        filename: str,
    ) -> str:
        safe_name = Path(filename).name.replace(" ", "_").replace("/", "_")
        return (
            f"cases/{case_id}/calculations/{calculation_id}/"
            f"versions/v{version_number}-{version_id}/{safe_name}"
        )


def _get_upload_size(file: UploadFile) -> int:
    stream = file.file
    pos = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(pos)
    return size
