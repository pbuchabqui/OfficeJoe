"""Service for initial document contradiction detection."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.db.models.document_contradiction import DocumentContradiction
from app.db.models.financial_statement_extraction import (
    FinancialStatementCompetency,
    FinancialStatementExtraction,
    FinancialStatementRubric,
)
from app.db.models.holerite_extraction import HoleriteExtraction, HoleriteVerba
from app.schemas.document_contradiction import (
    ComparedDocumentValue,
    DocumentContradictionComparisonResult,
    DocumentContradictionResponse,
)


HOLERITE_FINANCIAL_RUBRIC_VALUE_RULE = "holerite_financial_same_competencia_rubric_value"


@dataclass(frozen=True)
class _HoleriteRubric:
    extraction: HoleriteExtraction
    verba: HoleriteVerba


@dataclass(frozen=True)
class _FinancialRubric:
    extraction: FinancialStatementExtraction
    competency: FinancialStatementCompetency
    rubric: FinancialStatementRubric


async def compare_holerite_financial_statement_rubrics(
    db: AsyncSession,
    case_id: str,
    competencia: str,
) -> DocumentContradictionComparisonResult:
    """Compare payslip rubrics against financial statement rubrics.

    Initial rule only:
    same case + same competency + same rubric key + different numeric value.
    """
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    await db.execute(
        delete(DocumentContradiction).where(
            DocumentContradiction.case_id == case_id,
            DocumentContradiction.competencia == competencia,
            DocumentContradiction.rule_key == HOLERITE_FINANCIAL_RUBRIC_VALUE_RULE,
        )
    )

    holerite_rubrics = await _list_holerite_rubrics(db, case_id, competencia)
    financial_rubrics = await _list_financial_rubrics(db, case_id, competencia)
    financial_by_key = {
        _rubric_key(item.rubric.codigo, item.rubric.descricao): item
        for item in financial_rubrics
    }

    compared_count = 0
    contradictions: list[DocumentContradiction] = []

    for holerite_item in holerite_rubrics:
        key = _rubric_key(holerite_item.verba.codigo, holerite_item.verba.descricao)
        financial_item = financial_by_key.get(key)
        if financial_item is None:
            continue

        holerite_value = _decimal_or_none(holerite_item.verba.valor_decimal)
        financial_value = _decimal_or_none(financial_item.rubric.valor_decimal)
        if holerite_value is None or financial_value is None:
            continue

        compared_count += 1
        delta = holerite_value - financial_value
        if abs(delta) <= Decimal("0.01"):
            continue

        contradiction = DocumentContradiction(
            case_id=case_id,
            competencia=competencia,
            rule_key=HOLERITE_FINANCIAL_RUBRIC_VALUE_RULE,
            holerite_extraction_id=holerite_item.extraction.id,
            holerite_verba_id=holerite_item.verba.id,
            financial_statement_id=financial_item.extraction.id,
            financial_statement_rubric_id=financial_item.rubric.id,
            rubric_key=key,
            rubric_code=holerite_item.verba.codigo or financial_item.rubric.codigo,
            rubric_description=holerite_item.verba.descricao,
            holerite_value_raw=holerite_item.verba.valor_raw,
            holerite_value_decimal=float(holerite_value),
            financial_value_raw=financial_item.rubric.valor_raw,
            financial_value_decimal=float(financial_value),
            delta_value=float(delta),
            compared_values={
                "holerite": {
                    "extraction_id": holerite_item.extraction.id,
                    "verba_id": holerite_item.verba.id,
                    "value_raw": holerite_item.verba.valor_raw,
                    "value_decimal": float(holerite_value),
                },
                "financial_statement": {
                    "extraction_id": financial_item.extraction.id,
                    "rubric_id": financial_item.rubric.id,
                    "value_raw": financial_item.rubric.valor_raw,
                    "value_decimal": float(financial_value),
                },
            },
            notes="Valor da rubrica difere entre holerite extraído e ficha financeira extraída.",
        )
        db.add(contradiction)
        contradictions.append(contradiction)

    await db.flush()

    return DocumentContradictionComparisonResult(
        case_id=case_id,
        competencia=competencia,
        rule_key=HOLERITE_FINANCIAL_RUBRIC_VALUE_RULE,
        compared_count=compared_count,
        contradiction_count=len(contradictions),
        contradictions=[_to_response(item) for item in contradictions],
    )


async def _list_holerite_rubrics(
    db: AsyncSession,
    case_id: str,
    competencia: str,
) -> list[_HoleriteRubric]:
    result = await db.execute(
        select(HoleriteExtraction, HoleriteVerba)
        .join(HoleriteVerba, HoleriteVerba.holerite_id == HoleriteExtraction.id)
        .where(
            HoleriteExtraction.case_id == case_id,
            HoleriteExtraction.competencia == competencia,
        )
    )
    return [
        _HoleriteRubric(extraction=extraction, verba=verba)
        for extraction, verba in result.all()
    ]


async def _list_financial_rubrics(
    db: AsyncSession,
    case_id: str,
    competencia: str,
) -> list[_FinancialRubric]:
    result = await db.execute(
        select(
            FinancialStatementExtraction,
            FinancialStatementCompetency,
            FinancialStatementRubric,
        )
        .join(
            FinancialStatementCompetency,
            FinancialStatementCompetency.financial_statement_id == FinancialStatementExtraction.id,
        )
        .join(
            FinancialStatementRubric,
            FinancialStatementRubric.competency_id == FinancialStatementCompetency.id,
        )
        .where(
            FinancialStatementExtraction.case_id == case_id,
            FinancialStatementCompetency.competencia == competencia,
        )
    )
    return [
        _FinancialRubric(extraction=extraction, competency=competency, rubric=rubric)
        for extraction, competency, rubric in result.all()
    ]


def _rubric_key(code: str | None, description: str) -> str:
    if code:
        return f"codigo:{code.strip().lower()}"
    return f"descricao:{_normalize_description(description)}"


def _normalize_description(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _decimal_or_none(value: float | int | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _to_response(contradiction: DocumentContradiction) -> DocumentContradictionResponse:
    return DocumentContradictionResponse(
        id=contradiction.id,
        case_id=contradiction.case_id,
        competencia=contradiction.competencia,
        rule_key=contradiction.rule_key,
        rubric_key=contradiction.rubric_key,
        rubric_code=contradiction.rubric_code,
        rubric_description=contradiction.rubric_description,
        holerite=ComparedDocumentValue(
            extraction_id=contradiction.holerite_extraction_id,
            item_id=contradiction.holerite_verba_id,
            value_raw=contradiction.holerite_value_raw,
            value_decimal=contradiction.holerite_value_decimal,
        ),
        financial_statement=ComparedDocumentValue(
            extraction_id=contradiction.financial_statement_id,
            item_id=contradiction.financial_statement_rubric_id,
            value_raw=contradiction.financial_value_raw,
            value_decimal=contradiction.financial_value_decimal,
        ),
        delta_value=contradiction.delta_value,
        status=contradiction.status,
        created_at=contradiction.created_at,
    )
