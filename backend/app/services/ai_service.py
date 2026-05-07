"""
Serviço de IA com rastreabilidade completa.
Todo output indica fontes, páginas, grau de confiança e status de revisão humana.
Nenhuma conclusão técnica é gerada sem lastro documental.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.db.models.ai_output import AIOutputType, AIReviewStatus

logger = logging.getLogger("officejoe.ai_service")
settings = get_settings()


# ── Prompt templates com rastreabilidade obrigatória ─────────────────────────

SYSTEM_PROMPT = """Você é um assistente especializado em perícia contábil judicial e extrajudicial.

REGRAS OBRIGATÓRIAS:
1. Toda afirmação deve citar a fonte: [DOCUMENTO: {nome}, PÁG: {número}]
2. Informe o grau de confiança de cada conclusão (0-100%)
3. Nunca gere conclusões sem lastro documental explícito
4. Se não há documentação suficiente, diga claramente "INSUFICIENTE: [motivo]"
5. Separe fatos de inferências usando os rótulos: [FATO] e [INFERÊNCIA]
6. Toda resposta técnica deve ser marcada como "PENDENTE DE REVISÃO HUMANA"
7. Use terminologia técnica contábil/jurídica correta
"""

QUESITO_PROMPT_TEMPLATE = """
PROCESSO: {case_number}
QUESITO #{seq}: {question}

DOCUMENTOS DISPONÍVEIS:
{context_docs}

Responda ao quesito seguindo as regras obrigatórias do sistema.
Estruture a resposta em:
1. RESPOSTA DIRETA (máx. 2 parágrafos)
2. FUNDAMENTAÇÃO DOCUMENTAL (com citações obrigatórias)
3. LIMITAÇÕES E RESSALVAS
4. GRAU DE CONFIANÇA: X%
5. STATUS: PENDENTE DE REVISÃO HUMANA pelo perito responsável
"""


# ── Cliente Anthropic ─────────────────────────────────────────────────────────

class AnthropicClient:

    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY não configurada.")
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        except ImportError:
            raise ImportError("Instale o pacote 'anthropic': pip install anthropic")

    def complete(
        self,
        prompt: str,
        system: str = SYSTEM_PROMPT,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        import anthropic
        message = self._client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "content": message.content[0].text if message.content else "",
            "prompt_tokens": message.usage.input_tokens,
            "completion_tokens": message.usage.output_tokens,
            "model": message.model,
            "stop_reason": message.stop_reason,
        }


# ── Serviço principal ─────────────────────────────────────────────────────────

class AIService:

    def __init__(self) -> None:
        self._client: Optional[AnthropicClient] = None

    def _get_client(self) -> AnthropicClient:
        if self._client is None:
            self._client = AnthropicClient()
        return self._client

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()

    def _build_context_from_pages(self, pages_data: List[Dict[str, Any]]) -> str:
        """
        Constrói contexto formatado com rastreabilidade de página.
        Cada trecho tem referência explícita de documento e página.
        """
        parts = []
        for item in pages_data:
            doc_name = item.get("document_name", "Documento")
            page_num = item.get("page_number", "?")
            text = item.get("text", "").strip()
            if text:
                parts.append(f"[DOCUMENTO: {doc_name}, PÁG: {page_num}]\n{text[:2000]}")
        return "\n\n---\n\n".join(parts) if parts else "Nenhum documento disponível."

    def answer_quesito(
        self,
        question: str,
        seq_number: int,
        case_number: str,
        pages_context: List[Dict[str, Any]],
        requested_by_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Gera rascunho de resposta a quesito com:
        - Fontes rastreáveis
        - Grau de confiança
        - Status obrigatório de revisão humana
        - Flag has_documental_basis baseada no contexto disponível
        """
        if not pages_context:
            return {
                "output_text": (
                    "INSUFICIENTE: Não há documentos indexados disponíveis para "
                    "fundamentar a resposta a este quesito. "
                    "Providencie os documentos e reprocesse."
                ),
                "overall_confidence": 0.0,
                "sources": [],
                "has_documental_basis": False,
                "review_status": AIReviewStatus.PENDING_REVIEW.value,
                "ai_model": settings.AI_MODEL,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "prompt_hash": "",
                "output_type": AIOutputType.QUESITO_DRAFT.value,
            }

        context_str = self._build_context_from_pages(pages_context)
        prompt = QUESITO_PROMPT_TEMPLATE.format(
            case_number=case_number,
            seq=seq_number,
            question=question,
            context_docs=context_str,
        )
        prompt_hash = self._hash_prompt(prompt)

        try:
            client = self._get_client()
            response = client.complete(prompt, max_tokens=settings.AI_MAX_TOKENS)

            # Extrai fontes das páginas usadas no contexto
            sources = [
                {
                    "document_id": item.get("document_id"),
                    "document_name": item.get("document_name"),
                    "page_number": item.get("page_number"),
                }
                for item in pages_context
            ]

            return {
                "output_text": response["content"],
                "overall_confidence": None,  # Extraído do texto pelo revisor
                "sources": sources,
                "has_documental_basis": len(pages_context) > 0,
                "review_status": AIReviewStatus.PENDING_REVIEW.value,
                "ai_model": response["model"],
                "prompt_tokens": response["prompt_tokens"],
                "completion_tokens": response["completion_tokens"],
                "prompt_hash": prompt_hash,
                "output_type": AIOutputType.QUESITO_DRAFT.value,
            }
        except Exception as exc:
            logger.error("Falha na chamada de IA: %s", exc)
            raise

    def summarize_document(
        self,
        document_name: str,
        pages_context: List[Dict[str, Any]],
        requested_by_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Gera resumo estruturado de documento com rastreabilidade."""
        context_str = self._build_context_from_pages(pages_context)
        prompt = (
            f"Analise o documento '{document_name}' e gere um resumo estruturado.\n\n"
            f"CONTEÚDO (por página):\n{context_str}\n\n"
            "Estruture o resumo em:\n"
            "1. TIPO DE DOCUMENTO\n"
            "2. PERÍODO/DATA DE REFERÊNCIA\n"
            "3. PARTES ENVOLVIDAS (com fontes)\n"
            "4. PRINCIPAIS INFORMAÇÕES (com citações de página)\n"
            "5. RELEVÂNCIA PERICIAL\n"
            "6. LIMITAÇÕES IDENTIFICADAS\n"
            "STATUS: PENDENTE DE REVISÃO HUMANA"
        )
        prompt_hash = self._hash_prompt(prompt)

        try:
            client = self._get_client()
            response = client.complete(prompt)
            sources = [
                {"document_name": document_name, "page_number": item.get("page_number")}
                for item in pages_context
            ]
            return {
                "output_text": response["content"],
                "overall_confidence": None,
                "sources": sources,
                "has_documental_basis": len(pages_context) > 0,
                "review_status": AIReviewStatus.PENDING_REVIEW.value,
                "ai_model": response["model"],
                "prompt_tokens": response["prompt_tokens"],
                "completion_tokens": response["completion_tokens"],
                "prompt_hash": prompt_hash,
                "output_type": AIOutputType.SUMMARY.value,
            }
        except Exception as exc:
            logger.error("Falha no resumo de documento: %s", exc)
            raise


def get_ai_service() -> AIService:
    return AIService()
