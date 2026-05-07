from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_contradiction import DocumentContradiction
from app.db.models.financial_statement_extraction import (
    FinancialStatementCompetency,
    FinancialStatementExtraction,
    FinancialStatementRubric,
)
from app.db.models.holerite_extraction import HoleriteExtraction, HoleriteVerba
from app.services.document_contradiction_service import (
    HOLERITE_FINANCIAL_RUBRIC_VALUE_RULE,
    compare_holerite_financial_statement_rubrics,
)


@pytest.mark.asyncio
async def test_compare_holerite_and_financial_statement_rubrics_with_simulated_data(
    db_session: AsyncSession,
    sample_case,
):
    await _seed_compared_extractions(db_session, sample_case.id)

    result = await compare_holerite_financial_statement_rubrics(
        db_session,
        case_id=sample_case.id,
        competencia="05/2024",
    )

    assert result.case_id == sample_case.id
    assert result.competencia == "05/2024"
    assert result.rule_key == HOLERITE_FINANCIAL_RUBRIC_VALUE_RULE
    assert result.compared_count == 2
    assert result.contradiction_count == 1

    contradiction = result.contradictions[0]
    assert contradiction.rubric_code == "001"
    assert contradiction.rubric_description == "SALARIO BASE"
    assert contradiction.holerite.value_decimal == 3500.0
    assert contradiction.financial_statement.value_decimal == 3400.0
    assert contradiction.delta_value == 100.0

    stored = (
        await db_session.execute(select(DocumentContradiction))
    ).scalars().all()
    assert len(stored) == 1
    assert stored[0].status == "pendente"


@pytest.mark.asyncio
async def test_compare_document_contradictions_endpoint_returns_compared_values(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_case,
    perito_token: str,
):
    await _seed_compared_extractions(db_session, sample_case.id)
    await db_session.commit()

    response = await client.post(
        "/api/v1/document-contradictions/compare",
        json={"case_id": sample_case.id, "competencia": "05/2024"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == sample_case.id
    assert body["competencia"] == "05/2024"
    assert body["compared_count"] == 2
    assert body["contradiction_count"] == 1
    assert body["contradictions"][0]["holerite"]["value_decimal"] == 3500.0
    assert body["contradictions"][0]["financial_statement"]["value_decimal"] == 3400.0


async def _seed_compared_extractions(db_session: AsyncSession, case_id: str) -> None:
    holerite_doc = _document(case_id, "holerite.pdf", "holerite", "a")
    financial_doc = _document(case_id, "ficha-financeira.pdf", "ficha_financeira", "b")
    db_session.add_all([holerite_doc, financial_doc])
    await db_session.flush()

    holerite = HoleriteExtraction(
        id=str(uuid.uuid4()),
        document_id=holerite_doc.id,
        case_id=case_id,
        page_start=1,
        page_end=1,
        competencia="05/2024",
        extraction_status="extraido",
    )
    financial = FinancialStatementExtraction(
        id=str(uuid.uuid4()),
        document_id=financial_doc.id,
        case_id=case_id,
        page_start=1,
        page_end=1,
        periodo_inicio="05/2024",
        periodo_fim="05/2024",
        extraction_status="extraido",
    )
    db_session.add_all([holerite, financial])
    await db_session.flush()

    competency = FinancialStatementCompetency(
        id=str(uuid.uuid4()),
        financial_statement_id=financial.id,
        competencia="05/2024",
        section_index=0,
        confidence=0.95,
    )
    db_session.add(competency)
    await db_session.flush()

    db_session.add_all(
        [
            HoleriteVerba(
                id=str(uuid.uuid4()),
                holerite_id=holerite.id,
                line_index=1,
                codigo="001",
                descricao="SALARIO BASE",
                valor_raw="3.500,00",
                valor_decimal=3500.0,
                tipo="provento",
                confidence=0.94,
            ),
            HoleriteVerba(
                id=str(uuid.uuid4()),
                holerite_id=holerite.id,
                line_index=2,
                codigo="101",
                descricao="INSS",
                valor_raw="315,00",
                valor_decimal=315.0,
                tipo="desconto",
                confidence=0.9,
            ),
            FinancialStatementRubric(
                id=str(uuid.uuid4()),
                competency_id=competency.id,
                line_index=1,
                codigo="001",
                descricao="SALARIO BASE",
                rubric_type="provento",
                valor_raw="3.400,00",
                valor_decimal=3400.0,
                confidence=0.93,
            ),
            FinancialStatementRubric(
                id=str(uuid.uuid4()),
                competency_id=competency.id,
                line_index=2,
                codigo="101",
                descricao="INSS",
                rubric_type="desconto",
                valor_raw="315,00",
                valor_decimal=315.0,
                confidence=0.9,
            ),
        ]
    )
    await db_session.flush()


def _document(case_id: str, filename: str, category: str, hash_prefix: str) -> Document:
    return Document(
        id=str(uuid.uuid4()),
        case_id=case_id,
        original_filename=filename,
        display_name=filename,
        category=category,
        sha256_hash=hash_prefix * 64,
        file_size_bytes=1024,
        mime_type="application/pdf",
        storage_bucket="test-bucket",
        storage_key=f"test/{filename}",
        status="uploaded",
        is_original_preserved=True,
    )
