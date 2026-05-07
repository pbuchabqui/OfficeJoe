"""Mocked AI provider for generating preliminary answers to quesitos."""
from __future__ import annotations

import random
from typing import Optional


class MockedQuestionAIProvider:
    """Provider mockado para gerar respostas preliminares a quesitos com base em evidências."""

    def __init__(self):
        self.model_name = "mock-v1"

    def generate_answer(
        self,
        quesito_text: str,
        quesito_tema: Optional[str],
        quesito_tipo: Optional[str],
        evidence_texts: list[str],
    ) -> dict:
        """
        Gera uma resposta preliminar com base no quesito e evidências.

        Args:
            quesito_text: Texto do quesito
            quesito_tema: Tema/assunto do quesito
            quesito_tipo: Tipo de quesito (técnico, jurídico, etc)
            evidence_texts: Lista de textos de evidências vinculadas

        Returns:
            Dict com:
            - draft_text: Texto da resposta
            - confidence_score: Score de confiança (0.0 a 1.0)
            - evidence_summary: Resumo de como as evidências foram utilizadas
        """
        if not evidence_texts:
            raise ValueError("Evidências vinculadas são obrigatórias para gerar resposta")

        # Gera resposta preliminar mockada baseada nos inputs
        draft_text = self._generate_draft_text(quesito_text, quesito_tema, evidence_texts)
        confidence_score = self._calculate_confidence(len(evidence_texts), quesito_tema)
        evidence_summary = self._summarize_evidence_usage(evidence_texts)

        return {
            "draft_text": draft_text,
            "confidence_score": confidence_score,
            "evidence_summary": evidence_summary,
            "ai_model": self.model_name,
        }

    def _generate_draft_text(
        self,
        quesito_text: str,
        tema: Optional[str],
        evidence_texts: list[str],
    ) -> str:
        """Gera o texto da resposta preliminar."""
        # Template base para resposta técnica
        intro = self._get_intro(tema)
        evidence_analysis = self._analyze_evidence(evidence_texts)
        conclusion = self._get_conclusion(tema, len(evidence_texts))

        return f"""{intro}

ANÁLISE DAS EVIDÊNCIAS:

{evidence_analysis}

CONCLUSÃO PRELIMINAR:

{conclusion}

Nota: Esta é uma resposta preliminar gerada com IA mockada. Requer revisão humana antes de ser utilizada no laudo final."""

    def _get_intro(self, tema: Optional[str]) -> str:
        """Retorna introdução baseada no tema."""
        if tema == "contábil":
            return "Relativamente ao quesito formulado acerca de aspectos contábeis, apresentamos análise fundamentada nas seguintes evidências documentais:"
        elif tema == "financeiro":
            return "Quanto à questão de natureza financeira, nossa análise é baseada nos seguintes documentos de suporte:"
        elif tema == "trabalhista":
            return "Em resposta à questão trabalhista, fundamentamos nossa análise nas seguintes peças documentais:"
        else:
            return "Em resposta ao quesito, nossa análise técnica baseia-se nas seguintes evidências documentais:"

    def _analyze_evidence(self, evidence_texts: list[str]) -> str:
        """Analisa as evidências fornecidas."""
        analysis_lines = []
        for i, evidence in enumerate(evidence_texts, 1):
            excerpt = evidence[:100] + "..." if len(evidence) > 100 else evidence
            analysis_lines.append(f"{i}. Evidência: {excerpt}")

        if len(evidence_texts) == 1:
            reliability = "confiável"
        elif len(evidence_texts) <= 3:
            reliability = "adequadamente fundamentada"
        else:
            reliability = "fortemente fundamentada"

        return "\n".join(analysis_lines) + f"\n\nA análise encontra-se {reliability} pelas evidências apresentadas."

    def _get_conclusion(self, tema: Optional[str], evidence_count: int) -> str:
        """Retorna conclusão preliminar baseada no tema e quantidade de evidências."""
        if evidence_count >= 5:
            strength = "forte"
        elif evidence_count >= 3:
            strength = "moderada"
        else:
            strength = "inicial"

        conclusions = {
            "contábil": f"Com base nas evidências contábeis apresentadas, chegamos a uma conclusão {strength} acerca da questão formulada. A documentação analisada fornece respaldo técnico para as afirmações apresentadas.",
            "financeiro": f"A análise financeira das evidências proporciona uma avaliação {strength} do assunto. Os documentos revisados demonstram a situação financeira relevante.",
            "trabalhista": f"Relativamente aos aspectos trabalhistas investigados, a conclusão {strength} é corroborada pela documentação examinada.",
            "default": f"Baseando-nos nas evidências documentais compiladas, chegamos a uma conclusão {strength} acerca do quesito formulado.",
        }

        return conclusions.get(tema, conclusions["default"])

    def _summarize_evidence_usage(self, evidence_texts: list[str]) -> str:
        """Resumo de como as evidências foram utilizadas."""
        return f"Foram analisadas {len(evidence_texts)} evidência(s) para gerar esta resposta preliminar."

    def _calculate_confidence(self, evidence_count: int, tema: Optional[str]) -> float:
        """Calcula score de confiança baseado na quantidade e tema das evidências."""
        base_confidence = min(0.5 + (evidence_count * 0.1), 0.95)

        # Ajusta confiança baseada no tema
        if tema in ["contábil", "financeiro"]:
            base_confidence += 0.05
        elif tema == "trabalhista":
            base_confidence += 0.03

        # Adiciona variação small para simular variabilidade realista
        variation = random.uniform(-0.02, 0.02)
        final_confidence = max(0.4, min(1.0, base_confidence + variation))

        return round(final_confidence, 2)


def get_question_ai_provider() -> MockedQuestionAIProvider:
    """Factory para obter a instância do provider."""
    return MockedQuestionAIProvider()
