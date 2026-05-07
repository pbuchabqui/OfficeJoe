"""
Job assíncrono básico para processamento posterior de PDFs.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class ProcessingJobStatus(str, Enum):
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJobType(str, Enum):
    FILE_PAGE_REGISTRATION = "file_page_registration"


class ProcessingJob(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "processing_jobs"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default=ProcessingJobType.FILE_PAGE_REGISTRATION.value
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ProcessingJobStatus.QUEUED.value, index=True
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    document: Mapped["Document"] = relationship("Document")  # noqa: F821
    case: Mapped["Case"] = relationship("Case")  # noqa: F821
    created_by: Mapped[Optional["User"]] = relationship("User")  # noqa: F821
