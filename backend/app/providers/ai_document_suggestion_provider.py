"""Mocked AI provider for document suggestions."""
from __future__ import annotations

from app.schemas.ai_document_suggestion import DocumentSuggestion


class AIDocumentSuggestionProvider:
    """Mock AI provider that suggests documents based on case type and context."""

    # Base suggestions for each case type
    SUGGESTIONS_BY_CASE_TYPE = {
        "trabalhista": [
            DocumentSuggestion(
                document_type="Contrato de Trabalho",
                description="Documento essencial para análise das cláusulas contratuais e condições do vínculo",
                priority="crítica",
                estimated_impact="Impossível determinar direitos e deveres das partes sem contrato",
            ),
            DocumentSuggestion(
                document_type="RG/CPF do Reclamante",
                description="Identificação legal das partes para validação processual",
                priority="crítica",
                estimated_impact="Comprometimento da validade processual do caso",
            ),
            DocumentSuggestion(
                document_type="Contracheques",
                description="Documentos necessários para análise de holerites e cálculo de diferenças salariais",
                priority="alta",
                estimated_impact="Impossibilidade de comprovação de direitos trabalhistas",
            ),
            DocumentSuggestion(
                document_type="Carta de Demissão/TRCT",
                description="Documento comprobatório do término do contrato de trabalho",
                priority="alta",
                estimated_impact="Falta de clareza sobre causa e data da extinção contratual",
            ),
            DocumentSuggestion(
                document_type="Comunicação de Dispensa (CD)",
                description="Comprovação formal da rescisão do contrato",
                priority="média",
                estimated_impact="Incerteza sobre a data e motivo da desligação",
            ),
        ],
        "civel": [
            DocumentSuggestion(
                document_type="Contrato ou Documento Gerativo da Obrigação",
                description="Documento comprobatório do acordo ou obrigação em questão",
                priority="crítica",
                estimated_impact="Impossibilidade de comprovação do direito material",
            ),
            DocumentSuggestion(
                document_type="Correspondência entre as Partes",
                description="E-mails, mensagens ou cartas demonstrando a relação entre as partes",
                priority="alta",
                estimated_impact="Falta de contextualização do conflito",
            ),
            DocumentSuggestion(
                document_type="Comprovantes de Pagamento",
                description="Documentos comprobatórios de pagamentos realizados ou devidos",
                priority="alta",
                estimated_impact="Impossibilidade de comprovação de transações financeiras",
            ),
            DocumentSuggestion(
                document_type="Recibos/Notas Fiscais",
                description="Documentação de transações comerciais relevantes",
                priority="média",
                estimated_impact="Comprometimento da comprovação de operações comerciais",
            ),
        ],
        "fiscal": [
            DocumentSuggestion(
                document_type="Documentação Fiscal",
                description="Notas Fiscais, livros contábeis e registros de operações",
                priority="crítica",
                estimated_impact="Impossibilidade de comprovação de obrigações tributárias",
            ),
            DocumentSuggestion(
                document_type="Declaração de Imposto de Renda",
                description="DARFs, GUPs e comprovantes de pagamento de tributos",
                priority="alta",
                estimated_impact="Falta de comprovação de cumprimento de obrigações",
            ),
            DocumentSuggestion(
                document_type="Contabilidade e Balancetes",
                description="Registros contábeis e demonstrativos financeiros",
                priority="alta",
                estimated_impact="Impossibilidade de análise da situação financeira",
            ),
        ],
        "extrajudicial": [
            DocumentSuggestion(
                document_type="Correspondência de Aviso/Intimação",
                description="Comunicações extrajudiciais relevantes",
                priority="alta",
                estimated_impact="Falta de comprovação de tentativa de resolução",
            ),
            DocumentSuggestion(
                document_type="Documentação do Conflito Original",
                description="Contrato, recibo ou ato que originou o conflito",
                priority="crítica",
                estimated_impact="Impossibilidade de comprovação do direito material",
            ),
            DocumentSuggestion(
                document_type="Correspondência com Partes",
                description="E-mails e documentos trocados entre as partes",
                priority="média",
                estimated_impact="Falta de contexto do conflito",
            ),
        ],
        "arbitragem": [
            DocumentSuggestion(
                document_type="Cláusula Arbitral ou Acordo Arbitral",
                description="Documento comprovando a validade da arbitragem",
                priority="crítica",
                estimated_impact="Invalidade do processo arbitral",
            ),
            DocumentSuggestion(
                document_type="Documentação do Conflito Subjacente",
                description="Contrato ou acordo que gerou a disputa",
                priority="crítica",
                estimated_impact="Impossibilidade de análise do mérito",
            ),
            DocumentSuggestion(
                document_type="Regulamento da Arbitragem",
                description="Regras procedimentais aplicáveis ao processo",
                priority="alta",
                estimated_impact="Incerteza sobre procedimento adequado",
            ),
        ],
    }

    async def get_suggestions(
        self,
        case_id: str,
        case_type: str,
        context: str | None = None,
    ) -> list[DocumentSuggestion]:
        """Get suggested documents based on case type.

        Args:
            case_id: Case identifier
            case_type: Type of case (trabalhista, civil, administrativo, previdenciario)
            context: Optional additional context for refinement

        Returns:
            List of suggested documents
        """
        suggestions = self.SUGGESTIONS_BY_CASE_TYPE.get(case_type, [])

        if context and "pessoa física" in context.lower():
            suggestions = [
                s
                for s in suggestions
                if "CNPJ" not in s.document_type and "empresa" not in s.document_type.lower()
            ]

        if context and "empresa" in context.lower():
            suggestions = [
                s
                for s in suggestions
                if "RG/CPF" not in s.document_type or "CNPJ" in s.document_type
            ]

        return suggestions if suggestions else self._default_suggestions()

    def _default_suggestions(self) -> list[DocumentSuggestion]:
        """Return default suggestions for unknown case types."""
        return [
            DocumentSuggestion(
                document_type="Documentação Identificatória",
                description="RG, CPF ou CNPJ das partes envolvidas",
                priority="crítica",
                estimated_impact="Comprometimento da validade processual",
            ),
            DocumentSuggestion(
                document_type="Documento Base do Conflito",
                description="Contrato, correspondência ou ato que originou o conflito",
                priority="crítica",
                estimated_impact="Impossibilidade de comprovação do direito material",
            ),
            DocumentSuggestion(
                document_type="Correspondência Relevante",
                description="E-mails, cartas ou mensagens relacionadas às partes",
                priority="média",
                estimated_impact="Falta de contextualização do conflito",
            ),
        ]
