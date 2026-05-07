"""Service for validating evidence matrix items (proof matrix validation)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evidence_item import EvidenceItem
from app.db.models.evidence_matrix_item import EvidenceMatrixItem
from app.schemas.evidence_matrix_validator import Alert, AlertLevel, ValidationResult


async def validate_matrix_item(
    db: AsyncSession,
    matrix_id: str,
) -> ValidationResult:
    """
    Validate a matrix item for conclusiveness.

    Rules:
    - If item is conclusive (has result and impact), requires at least 1 validated evidence
    - Conclusive = result_found and technical_impact are non-empty AND status is "published"

    Returns ValidationResult with appropriate alerts.
    """
    matrix_item = await db.get(EvidenceMatrixItem, matrix_id)
    if not matrix_item:
        raise ValueError(f"Matrix item {matrix_id} not found")

    alerts: list[Alert] = []

    is_conclusive = (
        bool(matrix_item.result_found.strip())
        and bool(matrix_item.technical_impact.strip())
        and matrix_item.status == "published"
    )

    if not is_conclusive:
        return ValidationResult(
            matrix_id=matrix_id,
            is_valid=True,
            alerts=[],
            summary="Item não é conclusivo. Nenhuma validação de evidência requerida.",
        )

    if len(matrix_item.evidence_ids) == 0:
        alerts.append(
            Alert(
                level=AlertLevel.BLOQUEANTE,
                message="Item conclusivo sem nenhuma evidência vinculada",
                field="evidence_ids",
            )
        )
        return ValidationResult(
            matrix_id=matrix_id,
            is_valid=False,
            alerts=alerts,
            summary="Item conclusivo bloqueado: sem evidências vinculadas",
        )

    validated_evidence_count = await db.scalar(
        select(func.count(EvidenceItem.id)).where(
            (EvidenceItem.id.in_(matrix_item.evidence_ids))
            & (EvidenceItem.validation_status == "validated")
        )
    )

    if validated_evidence_count == 0:
        alerts.append(
            Alert(
                level=AlertLevel.CRÍTICO,
                message="Item conclusivo sem nenhuma evidência validada",
                field="evidence_ids",
            )
        )
        return ValidationResult(
            matrix_id=matrix_id,
            is_valid=False,
            alerts=alerts,
            summary="Item conclusivo bloqueado: nenhuma evidência validada",
        )

    total_evidence_count = len(matrix_item.evidence_ids)
    if validated_evidence_count < total_evidence_count:
        alerts.append(
            Alert(
                level=AlertLevel.ATENÇÃO,
                message=f"Item conclusivo com {total_evidence_count - validated_evidence_count} de {total_evidence_count} evidências não validadas",
                field="evidence_ids",
            )
        )

    alerts.append(
        Alert(
            level=AlertLevel.INFORMATIVO,
            message=f"Item conclusivo com {validated_evidence_count} evidência(s) validada(s)",
            field="evidence_ids",
        )
    )

    return ValidationResult(
        matrix_id=matrix_id,
        is_valid=True,
        alerts=alerts,
        summary=f"Item conclusivo válido com {validated_evidence_count}/{total_evidence_count} evidências validadas",
    )
