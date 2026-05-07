"""Registro lógico de página de um PDF."""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class FilePageInitialStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FilePage(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "file_pages"

    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    status_ocr: Mapped[str] = mapped_column(
        String(50), nullable=False, default=FilePageInitialStatus.PENDING.value
    )
    status_preview: Mapped[str] = mapped_column(
        String(50), nullable=False, default=FilePageInitialStatus.PENDING.value
    )
    preview_storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    average_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    file: Mapped["Document"] = relationship("Document")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("file_id", "page_number", name="uq_file_pages_file_page_number"),
    )
