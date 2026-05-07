from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.calculation import Calculation, CalculationVersion
from app.db.models.document import Document
from app.schemas.report import ReportCreateRequest
from app.schemas.report_attachment import ReportAttachmentCreateRequest
from app.services.report_attachment_service import (
    create_report_attachment,
    list_report_attachments,
)
from app.services.report_service import create_report


@pytest.mark.asyncio
async def test_create_report_attachments_numbers_by_type(
    db_session: AsyncSession,
    sample_case,
):
    report = await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(title="Laudo", report_type="trabalhista"),
    )

    first = await create_report_attachment(
        db_session,
        sample_case.id,
        report.id,
        ReportAttachmentCreateRequest(
            attachment_type="anexo",
            title="Documentos do processo",
        ),
    )
    second = await create_report_attachment(
        db_session,
        sample_case.id,
        report.id,
        ReportAttachmentCreateRequest(
            attachment_type="anexo",
            title="Contracheques",
        ),
    )
    appendix = await create_report_attachment(
        db_session,
        sample_case.id,
        report.id,
        ReportAttachmentCreateRequest(
            attachment_type="apendice",
            title="Memória técnica",
        ),
    )

    assert first.number == 1
    assert second.number == 2
    assert appendix.number == 1

    attachments = await list_report_attachments(db_session, sample_case.id, report.id)
    assert [item.title for item in attachments] == [
        "Documentos do processo",
        "Contracheques",
        "Memória técnica",
    ]


@pytest.mark.asyncio
async def test_create_report_attachment_links_file_or_calculation_version(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    report = await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(title="Laudo", report_type="contabil"),
    )
    document = Document(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        original_filename="holerite.pdf",
        category="holerite",
        sha256_hash="a" * 64,
        file_size_bytes=128,
        mime_type="application/pdf",
        storage_bucket="test-bucket",
        storage_key=f"test/{uuid.uuid4()}/holerite.pdf",
        uploaded_by_id=perito_user.id,
    )
    calculation = Calculation(
        id=str(uuid.uuid4()),
        case_id=sample_case.id,
        calculation_type="liquidacao",
        description="Cálculo inicial",
        responsible_user_id=perito_user.id,
    )
    version = CalculationVersion(
        id=str(uuid.uuid4()),
        calculation_id=calculation.id,
        version_number=1,
        original_filename="calculo.xlsx",
        storage_bucket="test-bucket",
        storage_key=f"test/{uuid.uuid4()}/calculo.xlsx",
        sha256_hash="b" * 64,
        file_size_bytes=256,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        created_by_id=perito_user.id,
    )
    db_session.add_all([document, calculation, version])
    await db_session.flush()

    file_attachment = await create_report_attachment(
        db_session,
        sample_case.id,
        report.id,
        ReportAttachmentCreateRequest(
            attachment_type="anexo",
            title="Holerite vinculado",
            file_id=document.id,
        ),
    )
    calculation_attachment = await create_report_attachment(
        db_session,
        sample_case.id,
        report.id,
        ReportAttachmentCreateRequest(
            attachment_type="apendice",
            title="Cálculo vinculado",
            calculation_version_id=version.id,
        ),
    )

    assert file_attachment.file_id == document.id
    assert file_attachment.calculation_version_id is None
    assert calculation_attachment.calculation_version_id == version.id
    assert calculation_attachment.file_id is None


@pytest.mark.asyncio
async def test_report_attachment_rejects_source_outside_case(
    db_session: AsyncSession,
    sample_case,
    perito_user,
):
    other_case = type(sample_case)(
        id=str(uuid.uuid4()),
        case_number=f"{uuid.uuid4().hex[:7]}-57.2024.5.02.0001",
        case_type=sample_case.case_type,
        title="Outro processo",
        status=sample_case.status,
        responsible_user_id=perito_user.id,
    )
    db_session.add(other_case)
    report = await create_report(
        db_session,
        sample_case.id,
        ReportCreateRequest(title="Laudo", report_type="trabalhista"),
    )
    document = Document(
        id=str(uuid.uuid4()),
        case_id=other_case.id,
        original_filename="fora.pdf",
        category="outro",
        sha256_hash="c" * 64,
        file_size_bytes=128,
        mime_type="application/pdf",
        storage_bucket="test-bucket",
        storage_key=f"test/{uuid.uuid4()}/fora.pdf",
        uploaded_by_id=perito_user.id,
    )
    db_session.add(document)
    await db_session.flush()

    with pytest.raises(ValueError, match="does not belong to case"):
        await create_report_attachment(
            db_session,
            sample_case.id,
            report.id,
            ReportAttachmentCreateRequest(
                attachment_type="anexo",
                title="Arquivo de outro processo",
                file_id=document.id,
            ),
        )


@pytest.mark.asyncio
async def test_report_attachments_endpoint_creates_and_lists(
    client: AsyncClient,
    sample_case,
    perito_token: str,
):
    report_response = await client.post(
        f"/api/v1/reports?case_id={sample_case.id}",
        json={"title": "Laudo", "report_type": "trabalhista"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert report_response.status_code == 201
    report_id = report_response.json()["id"]

    create_response = await client.post(
        f"/api/v1/cases/{sample_case.id}/reports/{report_id}/attachments",
        json={"attachment_type": "anexo", "title": "Documentos-base"},
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert create_response.status_code == 201
    assert create_response.json()["number"] == 1
    assert create_response.json()["attachment_type"] == "anexo"

    list_response = await client.get(
        f"/api/v1/cases/{sample_case.id}/reports/{report_id}/attachments",
        headers={"Authorization": f"Bearer {perito_token}"},
    )
    assert list_response.status_code == 200
    assert [item["title"] for item in list_response.json()] == ["Documentos-base"]
