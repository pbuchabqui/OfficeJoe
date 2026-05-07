from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.processing_job import ProcessingJob
from app.db.session import get_db
from app.schemas.processing_job import ProcessingJobResponse

router = APIRouter(prefix="/processing-jobs", tags=["Processing Jobs"])


@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_processing_job(
    job_id: str,
    current_user=Depends(require_permission("document:read")),
    db: AsyncSession = Depends(get_db),
) -> ProcessingJobResponse:
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job de processamento não encontrado.",
        )
    return ProcessingJobResponse.model_validate(job)
