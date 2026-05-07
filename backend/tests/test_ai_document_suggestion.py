"""Tests for AI document suggestion service and endpoint."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case, CaseStatus, CaseType
from app.providers.ai_document_suggestion_provider import AIDocumentSuggestionProvider
from app.schemas.ai_document_suggestion import AIDocumentSuggestionRequest
from app.services.ai_document_suggestion_service import get_document_suggestions


async def _make_case(db: AsyncSession, user_id: str, case_type: str) -> Case:
    """Helper to create a test case."""
    case = Case(
        id=str(uuid.uuid4()),
        case_number=f"000{uuid.uuid4().hex[:4]}-56.2024.5.02.0000",
        case_type=case_type,
        title="Test Case",
        status=CaseStatus.PLANEJAMENTO.value,
        responsible_user_id=user_id,
    )
    db.add(case)
    await db.flush()
    return case


# ── Provider Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_provider_trabalhista_suggestions():
    """Provider retorna sugestões relevantes para caso trabalhista."""
    provider = AIDocumentSuggestionProvider()

    suggestions = await provider.get_suggestions(
        case_id="test-case",
        case_type="trabalhista",
    )

    assert len(suggestions) > 0
    assert any("Contrato" in s.document_type for s in suggestions)
    assert any("RG/CPF" in s.document_type for s in suggestions)
    assert any("Contracheques" in s.document_type for s in suggestions)

    for suggestion in suggestions:
        assert suggestion.document_type
        assert suggestion.description
        assert suggestion.priority in ["baixa", "média", "alta", "crítica"]
        assert suggestion.estimated_impact


@pytest.mark.asyncio
async def test_provider_civel_suggestions():
    """Provider retorna sugestões relevantes para caso cível."""
    provider = AIDocumentSuggestionProvider()

    suggestions = await provider.get_suggestions(
        case_id="test-case",
        case_type="civel",
    )

    assert len(suggestions) > 0
    assert any("Contrato" in s.document_type for s in suggestions)
    assert any("Pagamento" in s.document_type or "Correspondência" in s.document_type for s in suggestions)

    for suggestion in suggestions:
        assert suggestion.priority in ["baixa", "média", "alta", "crítica"]


@pytest.mark.asyncio
async def test_provider_fiscal_suggestions():
    """Provider retorna sugestões relevantes para caso fiscal."""
    provider = AIDocumentSuggestionProvider()

    suggestions = await provider.get_suggestions(
        case_id="test-case",
        case_type="fiscal",
    )

    assert len(suggestions) > 0
    assert any("Fiscal" in s.document_type for s in suggestions)

    for suggestion in suggestions:
        assert suggestion.document_type
        assert suggestion.priority in ["baixa", "média", "alta", "crítica"]


@pytest.mark.asyncio
async def test_provider_arbitragem_suggestions():
    """Provider retorna sugestões relevantes para caso de arbitragem."""
    provider = AIDocumentSuggestionProvider()

    suggestions = await provider.get_suggestions(
        case_id="test-case",
        case_type="arbitragem",
    )

    assert len(suggestions) > 0
    assert any("Arbitral" in s.document_type or "Cláusula" in s.document_type for s in suggestions)

    for suggestion in suggestions:
        assert suggestion.priority in ["baixa", "média", "alta", "crítica"]


@pytest.mark.asyncio
async def test_provider_unknown_case_type_default_suggestions():
    """Provider retorna sugestões padrão para tipo desconhecido."""
    provider = AIDocumentSuggestionProvider()

    suggestions = await provider.get_suggestions(
        case_id="test-case",
        case_type="tipo_desconhecido",
    )

    assert len(suggestions) > 0
    assert any("Documentação Identificatória" in s.document_type for s in suggestions)

    for suggestion in suggestions:
        assert suggestion.priority in ["baixa", "média", "alta", "crítica"]


@pytest.mark.asyncio
async def test_provider_context_pessoa_fisica():
    """Provider filtra sugestões baseado em contexto de pessoa física."""
    provider = AIDocumentSuggestionProvider()

    suggestions = await provider.get_suggestions(
        case_id="test-case",
        case_type="trabalhista",
        context="pessoa física",
    )

    assert len(suggestions) > 0
    assert not any("CNPJ" in s.document_type for s in suggestions)


@pytest.mark.asyncio
async def test_provider_context_empresa():
    """Provider filtra sugestões baseado em contexto de empresa."""
    provider = AIDocumentSuggestionProvider()

    suggestions = await provider.get_suggestions(
        case_id="test-case",
        case_type="civel",
        context="empresa",
    )

    assert len(suggestions) > 0


# ── Service Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_document_suggestions_success(db_session: AsyncSession):
    """Obter sugestões de documentos para caso existente."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="ai-user1@teste.com",
        full_name="AI User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id, "trabalhista")
    await db_session.commit()

    response = await get_document_suggestions(db_session, case.id)

    assert response.case_id == case.id
    assert len(response.suggestions) > 0
    assert response.total_suggestions == len(response.suggestions)
    assert any("Contrato" in s.document_type for s in response.suggestions)


@pytest.mark.asyncio
async def test_get_document_suggestions_with_context(db_session: AsyncSession):
    """Obter sugestões com contexto adicional."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="ai-user2@teste.com",
        full_name="AI User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id, "civel")
    await db_session.commit()

    response = await get_document_suggestions(
        db_session, case.id, context="Disputa sobre contrato de serviços"
    )

    assert response.case_id == case.id
    assert len(response.suggestions) > 0
    assert response.total_suggestions > 0


@pytest.mark.asyncio
async def test_get_document_suggestions_case_not_found(db_session: AsyncSession):
    """Erro ao solicitar sugestões para caso inexistente."""
    with pytest.raises(ValueError, match="Case .* not found"):
        await get_document_suggestions(db_session, "invalid-case")


@pytest.mark.asyncio
async def test_get_document_suggestions_all_case_types(db_session: AsyncSession):
    """Obter sugestões para todos os tipos de processo."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="ai-user3@teste.com",
        full_name="AI User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case_types = [
        "trabalhista",
        "civel",
        "fiscal",
        "extrajudicial",
        "arbitragem",
    ]

    for case_type in case_types:
        case = await _make_case(db_session, user.id, case_type)
        await db_session.commit()

        response = await get_document_suggestions(db_session, case.id)

        assert response.case_id == case.id
        assert len(response.suggestions) > 0
        assert response.total_suggestions > 0


@pytest.mark.asyncio
async def test_get_document_suggestions_response_structure(db_session: AsyncSession):
    """Verificar estrutura correta da resposta."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="ai-user4@teste.com",
        full_name="AI User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id, "trabalhista")
    await db_session.commit()

    response = await get_document_suggestions(db_session, case.id)

    assert hasattr(response, "case_id")
    assert hasattr(response, "suggestions")
    assert hasattr(response, "total_suggestions")

    for suggestion in response.suggestions:
        assert hasattr(suggestion, "document_type")
        assert hasattr(suggestion, "description")
        assert hasattr(suggestion, "priority")
        assert hasattr(suggestion, "estimated_impact")


@pytest.mark.asyncio
async def test_get_document_suggestions_criticality_levels(db_session: AsyncSession):
    """Verificar que sugestões incluem diferentes níveis de criticidade."""
    from app.db.models.user import User
    from app.core.security import hash_password

    user = User(
        id=str(uuid.uuid4()),
        email="ai-user5@teste.com",
        full_name="AI User",
        hashed_password=hash_password("SenhaSegura123!"),
        role="perito",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    case = await _make_case(db_session, user.id, "trabalhista")
    await db_session.commit()

    response = await get_document_suggestions(db_session, case.id)

    priorities = {s.priority for s in response.suggestions}
    assert "alta" in priorities or "crítica" in priorities


# ── Endpoint Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_suggestion_endpoint_success(client, perito_token, sample_case):
    """POST /ai/document-suggestions retorna sugestões com sucesso."""
    response = await client.post(
        "/api/v1/ai/document-suggestions",
        json={"case_id": sample_case.id},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == sample_case.id
    assert len(data["suggestions"]) > 0
    assert data["total_suggestions"] > 0


@pytest.mark.asyncio
async def test_suggestion_endpoint_with_context(client, perito_token, sample_case):
    """POST /ai/document-suggestions com contexto adicional."""
    payload = AIDocumentSuggestionRequest(
        case_id=sample_case.id,
        context="Disputa comercial entre empresa e fornecedor",
    )

    response = await client.post(
        "/api/v1/ai/document-suggestions",
        json=payload.model_dump(),
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == sample_case.id
    assert data["total_suggestions"] > 0


@pytest.mark.asyncio
async def test_suggestion_endpoint_case_not_found(client, perito_token):
    """POST /ai/document-suggestions retorna 404 para caso inexistente."""
    payload = AIDocumentSuggestionRequest(case_id="invalid-case")

    response = await client.post(
        "/api/v1/ai/document-suggestions",
        json=payload.model_dump(),
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_suggestion_endpoint_response_format(client, perito_token, sample_case):
    """POST /ai/document-suggestions retorna formato esperado."""
    response = await client.post(
        "/api/v1/ai/document-suggestions",
        json={"case_id": sample_case.id},
        headers={"Authorization": f"Bearer {perito_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "case_id" in data
    assert "suggestions" in data
    assert "total_suggestions" in data

    for suggestion in data["suggestions"]:
        assert "document_type" in suggestion
        assert "description" in suggestion
        assert "priority" in suggestion
        assert "estimated_impact" in suggestion
