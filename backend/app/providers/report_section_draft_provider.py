"""Mock provider for report section draft generation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportSectionDraftResult:
    content: str
    provider: str
    model: str


class MockReportSectionDraftProvider:
    """Deterministic provider used for tests and initial wiring."""

    provider_name = "mock"
    model_name = "mock-report-section-draft-v1"

    async def generate_section_draft(
        self,
        section_title: str,
        report_title: str,
        report_type: str,
        context: str | None = None,
        instructions: str | None = None,
    ) -> ReportSectionDraftResult:
        parts = [
            f"Minuta da seção: {section_title}.",
            f"Laudo: {report_title} ({report_type}).",
        ]
        if context:
            parts.append(f"Contexto considerado: {context.strip()}.")
        if instructions:
            parts.append(f"Instruções aplicadas: {instructions.strip()}.")
        parts.append("Texto gerado por provider mockado para revisão técnica posterior.")

        return ReportSectionDraftResult(
            content="\n\n".join(parts),
            provider=self.provider_name,
            model=self.model_name,
        )
