"""Inventário automático de autos: grupos de páginas consecutivas por classe documental."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKey


class DocumentInventoryItem(Base, UUIDPrimaryKey):
    __tablename__ = "document_inventory_items"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_class: Mapped[str] = mapped_column(String(100), nullable=False)
    start_page: Mapped[int] = mapped_column(Integer, nullable=False)
    end_page: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # Correção manual
    custom_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    edited_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship("Document")  # noqa: F821
    edited_by: Mapped["User"] = relationship("User")  # noqa: F821
