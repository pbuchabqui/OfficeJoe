"""Service for AI document suggestions."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.case import Case
from app.providers.ai_document_suggestion_provider import AIDocumentSuggestionProvider
from app.schemas.ai_document_suggestion import AIDocumentSuggestionResponse


async def get_document_suggestions(
    db: AsyncSession,
    case_id: str,
    context: str | None = None,
) -> AIDocumentSuggestionResponse:
    """Get AI suggestions for missing documents in a case.

    Validates:
    - Case exists
    - Generates suggestions based on case type and context

    Args:
        db: Database session
        case_id: Case identifier
        context: Optional additional context for analysis

    Returns:
        AIDocumentSuggestionResponse with suggested documents
    """
    case = await db.get(Case, case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")

    provider = AIDocumentSuggestionProvider()
    suggestions = await provider.get_suggestions(
        case_id=case_id,
        case_type=case.case_type,
        context=context,
    )

    return AIDocumentSuggestionResponse(
        case_id=case_id,
        suggestions=suggestions,
        total_suggestions=len(suggestions),
    )
