"""
Inventário automático dos autos.

Agrupa páginas consecutivas com a mesma classe documental em itens de inventário.
Cada geração substitui completamente o inventário anterior do documento.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

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
