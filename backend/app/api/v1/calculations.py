"""Endpoints for calculation control."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.schemas.calculation import (
    CalculationCreateRequest,
    CalculationResponse,
    CalculationVersionResponse,
)
from app.services.calculation_service import CalculationService

router = APIRouter(prefix="/cases/{case_id}/calculations", tags=["Cálculos"])


@router.post(
    "",
    response_model=CalculationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar controle de cálculo",
)
async def create_calculation_endpoint(
    case_id: str,
    payload: CalculationCreateRequest,
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> CalculationResponse:
    svc = CalculationService(db)
    try:
        calculation = await svc.create_calculation(case_id, payload)
        await db.commit()
        await db.refresh(calculation)
        return CalculationResponse.model_validate(calculation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{calculation_id}/versions",
    response_model=CalculationVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar nova versão de arquivo de cálculo",
)
async def upload_calculation_version_endpoint(
    case_id: str,
    calculation_id: str,
    file: UploadFile = File(...),
    premises: str | None = Form(default=None),
    methodology: str | None = Form(default=None),
    current_user=Depends(require_permission("extraction:write")),
    db: AsyncSession = Depends(get_db),
) -> CalculationVersionResponse:
    svc = CalculationService(db)
    try:
        version = await svc.upload_calculation_version(
            case_id=case_id,
            calculation_id=calculation_id,
            file=file,
            premises=premises,
            methodology=methodology,
            created_by_id=current_user.id,
        )
        await db.commit()
        await db.refresh(version)
        return CalculationVersionResponse.model_validate(version)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
