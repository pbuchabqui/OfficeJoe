"""
Inventário automático dos autos.

Agrupa páginas consecutivas com a mesma classe documental em itens de inventário.
Cada geração substitui completamente o inventário anterior do documento.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, log_audit
from app.db.models.audit_log import AuditLog
from app.db.models.document_inventory_item import DocumentInventoryItem
from app.db.models.page_classification import PageClassification


def _group_consecutive(
    classifications: list[PageClassification],
) -> list[dict]:
    """
    Algoritmo de agrupamento: percorre classificações ordenadas por page_number
    e acumula grupos enquanto a document_class não mudar.
    """
    groups: list[dict] = []
    if not classifications:
        return groups

    current_class = classifications[0].document_class
    start_page = classifications[0].page_number
    end_page = classifications[0].page_number
    confidence_sum = classifications[0].confidence
    count = 1

    for cls in classifications[1:]:
        if cls.document_class == current_class:
            end_page = cls.page_number
            confidence_sum += cls.confidence
            count += 1
        else:
            groups.append(
                {
                    "document_class": current_class,
                    "start_page": start_page,
                    "end_page": end_page,
                    "page_count": end_page - start_page + 1,
                    "confidence_avg": confidence_sum / count,
                }
            )
            current_class = cls.document_class
            start_page = cls.page_number
            end_page = cls.page_number
            confidence_sum = cls.confidence
            count = 1

    groups.append(
        {
            "document_class": current_class,
            "start_page": start_page,
            "end_page": end_page,
            "page_count": end_page - start_page + 1,
            "confidence_avg": confidence_sum / count,
        }
    )
    return groups


async def generate_inventory(
    db: AsyncSession,
    document_id: str,
) -> List[DocumentInventoryItem]:
    """
    Gera (ou regenera) o inventário para um documento.
    Remove itens anteriores, agrupa páginas por classe e persiste os novos itens.
    """
    # Remove inventário anterior
    await db.execute(
        delete(DocumentInventoryItem).where(
            DocumentInventoryItem.document_id == document_id
        )
    )

    # Busca classificações ordenadas por página
    result = await db.execute(
        select(PageClassification)
        .where(PageClassification.file_id == document_id)
        .order_by(PageClassification.page_number.asc())
    )
    classifications = list(result.scalars().all())

    generated_at = datetime.now(timezone.utc)
    groups = _group_consecutive(classifications)

    items: list[DocumentInventoryItem] = []
    for g in groups:
        item = DocumentInventoryItem(
            document_id=document_id,
            document_class=g["document_class"],
            start_page=g["start_page"],
            end_page=g["end_page"],
            page_count=g["page_count"],
            confidence_avg=g["confidence_avg"],
            generated_at=generated_at,
        )
        db.add(item)
        items.append(item)

    await db.flush()
    return items


async def list_inventory(
    db: AsyncSession,
    document_id: str,
) -> List[DocumentInventoryItem]:
    """Retorna o inventário atual de um documento, ordenado por página inicial."""
    result = await db.execute(
        select(DocumentInventoryItem)
        .where(DocumentInventoryItem.document_id == document_id)
        .order_by(DocumentInventoryItem.start_page.asc())
    )
    return list(result.scalars().all())


async def update_inventory_item(
    db: AsyncSession,
    item: DocumentInventoryItem,
    *,
    custom_label: Optional[str] = None,
    document_class: Optional[str] = None,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    is_relevant: Optional[bool] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """
    Atualiza um item de inventário e registra auditoria.
    Valida start_page <= end_page. Retorna dict com before/after para auditoria.
    """
    changes = {}

    if custom_label is not None and custom_label != item.custom_label:
        changes["custom_label"] = {"before": item.custom_label, "after": custom_label}
        item.custom_label = custom_label

    if document_class is not None and document_class != item.document_class:
        changes["document_class"] = {"before": item.document_class, "after": document_class}
        item.document_class = document_class

    if start_page is not None and start_page != item.start_page:
        changes["start_page"] = {"before": item.start_page, "after": start_page}
        item.start_page = start_page

    if end_page is not None and end_page != item.end_page:
        changes["end_page"] = {"before": item.end_page, "after": end_page}
        item.end_page = end_page

    if is_relevant is not None and is_relevant != item.is_relevant:
        changes["is_relevant"] = {"before": item.is_relevant, "after": is_relevant}
        item.is_relevant = is_relevant

    # Valida integridade: start_page <= end_page
    if item.start_page > item.end_page:
        raise ValueError(
            f"start_page ({item.start_page}) não pode ser maior que end_page ({item.end_page})"
        )

    # Recalcula page_count se necessário
    item.page_count = item.end_page - item.start_page + 1
    item.edited_by_id = user_id
    item.edited_at = datetime.now(timezone.utc)

    await db.flush()

    # Log de auditoria
    if changes or user_id:
        entry = log_audit(
            action=AuditAction.INVENTORY_ITEM_EDITED,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            resource_type="inventory_item",
            resource_id=item.id,
            details={
                "document_id": item.document_id,
                "changes": changes,
            },
        )
        log = AuditLog(
            id=entry.id,
            timestamp=entry.timestamp,
            action=entry.action.value,
            success=entry.success,
            user_id=entry.user_id,
            user_email=entry.user_email,
            ip_address=entry.ip_address,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            details=entry.details,
        )
        db.add(log)
        await db.flush()

    return changes
