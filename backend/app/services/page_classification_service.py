"""
Classificação documental por IA com provider mockável.
Não chama modelos externos.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.file_page import FilePage
from app.db.models.page_classification import DocumentClass, PageClassification
from app.db.models.page_text_block import PageTextBlock
from app.schemas.page_classification import ClassificationAIResponse, DOCUMENT_CLASS_LABELS


class PageClassificationProvider(Protocol):
    provider_name: str
    model_name: str

    async def classify_page(self, text: str) -> ClassificationAIResponse:
        ...


class MockPageClassificationProvider:
    provider_name = "mock"
    model_name = "mock-document-classifier-v1"

    async def classify_page(self, text: str) -> ClassificationAIResponse:
        normalized = text.lower()
        if not normalized.strip():
            return ClassificationAIResponse(
                document_class=DocumentClass.DOCUMENTO_ILEGIVEL.value,
                confidence=0.4,
                rationale="Sem texto OCR disponível para classificar.",
            )

        keyword_map = [
            ("holerite", DocumentClass.HOLERITE.value),
            ("contracheque", DocumentClass.HOLERITE.value),
            ("ficha financeira", DocumentClass.FICHA_FINANCEIRA.value),
            ("cartão ponto", DocumentClass.CARTAO_PONTO.value),
            ("sentença", DocumentClass.SENTENCA.value),
            ("acórdão", DocumentClass.ACORDAO.value),
            ("decisão", DocumentClass.DECISAO.value),
            ("petição inicial", DocumentClass.PETICAO_INICIAL.value),
            ("contestação", DocumentClass.CONTESTACAO.value),
            ("laudo", DocumentClass.LAUDO.value),
            ("parecer", DocumentClass.PARECER.value),
            ("contrato", DocumentClass.CONTRATO.value),
            ("extrato", DocumentClass.EXTRATO.value),
            ("nota fiscal", DocumentClass.NOTA_FISCAL.value),
            ("cct", DocumentClass.CCT.value),
            ("act", DocumentClass.ACT.value),
            ("trct", DocumentClass.TRCT.value),
            ("e-mail", DocumentClass.EMAIL.value),
            ("email", DocumentClass.EMAIL.value),
            ("planilha", DocumentClass.PLANILHA.value),
        ]
        for keyword, document_class in keyword_map:
            if keyword in normalized:
                return ClassificationAIResponse(
                    document_class=document_class,
                    confidence=0.8,
                    rationale=f"Provider mock encontrou o termo '{keyword}'.",
                )
        return ClassificationAIResponse(
            document_class=DocumentClass.OUTRO.value,
            confidence=0.5,
            rationale="Provider mock não encontrou termos específicos.",
        )


def get_page_classification_provider() -> PageClassificationProvider:
    return MockPageClassificationProvider()


class PageClassificationService:
    def __init__(
        self,
        db: AsyncSession,
        provider: PageClassificationProvider | None = None,
    ) -> None:
        self._db = db
        self._provider = provider or get_page_classification_provider()

    async def classify_page(
        self,
        case_id: str,
        document_id: str,
        file_page_id: str,
    ) -> PageClassification:
        file_page = await self._get_file_page(case_id, document_id, file_page_id)
        text = await self._get_page_text(file_page_id)
        ai_response = await self._provider.classify_page(text)
        self._validate_ai_response(ai_response)

        existing = await self._db.execute(
            select(PageClassification).where(PageClassification.file_page_id == file_page_id)
        )
        classification = existing.scalar_one_or_none()
        if not classification:
            classification = PageClassification(
                id=str(uuid.uuid4()),
                file_page_id=file_page.id,
                file_id=file_page.file_id,
                page_number=file_page.page_number,
            )
            self._db.add(classification)

        classification.document_class = ai_response.document_class
        classification.confidence = ai_response.confidence
        classification.rationale = ai_response.rationale
        classification.provider = self._provider.provider_name
        classification.model_name = self._provider.model_name
        classification.raw_response = ai_response.model_dump()
        await self._db.flush()
        return classification

    async def get_classification(
        self,
        case_id: str,
        document_id: str,
        file_page_id: str,
    ) -> PageClassification | None:
        await self._get_file_page(case_id, document_id, file_page_id)
        result = await self._db.execute(
            select(PageClassification).where(PageClassification.file_page_id == file_page_id)
        )
        return result.scalar_one_or_none()

    async def approve_classification(
        self,
        case_id: str,
        document_id: str,
        file_page_id: str,
        validated_by: str,
    ) -> PageClassification:
        classification = await self._get_existing_classification(case_id, document_id, file_page_id)
        self._mark_validated(classification, validated_by)
        await self._db.flush()
        return classification

    async def correct_classification(
        self,
        case_id: str,
        document_id: str,
        file_page_id: str,
        document_class: str,
        validated_by: str,
    ) -> PageClassification:
        if document_class not in DOCUMENT_CLASS_LABELS:
            raise ValueError(f"Classe documental inválida: {document_class}")
        classification = await self._get_existing_classification(case_id, document_id, file_page_id)
        classification.document_class = document_class
        self._mark_validated(classification, validated_by)
        await self._db.flush()
        return classification

    async def _get_file_page(
        self,
        case_id: str,
        document_id: str,
        file_page_id: str,
    ) -> FilePage:
        result = await self._db.execute(
            select(FilePage)
            .join(Document, Document.id == FilePage.file_id)
            .where(
                FilePage.id == file_page_id,
                FilePage.file_id == document_id,
                Document.case_id == case_id,
            )
        )
        file_page = result.scalar_one_or_none()
        if not file_page:
            raise ValueError("Página não encontrada.")
        return file_page

    async def _get_page_text(self, file_page_id: str) -> str:
        result = await self._db.execute(
            select(PageTextBlock)
            .where(PageTextBlock.file_page_id == file_page_id)
            .order_by(PageTextBlock.y0, PageTextBlock.x0)
        )
        return " ".join(block.text for block in result.scalars().all())

    async def _get_existing_classification(
        self,
        case_id: str,
        document_id: str,
        file_page_id: str,
    ) -> PageClassification:
        await self._get_file_page(case_id, document_id, file_page_id)
        result = await self._db.execute(
            select(PageClassification).where(PageClassification.file_page_id == file_page_id)
        )
        classification = result.scalar_one_or_none()
        if not classification:
            raise ValueError("Classificação não encontrada.")
        return classification

    def _mark_validated(
        self,
        classification: PageClassification,
        validated_by: str,
    ) -> None:
        classification.human_validated = True
        classification.validated_by = validated_by
        classification.validated_at = datetime.now(timezone.utc)

    def _validate_ai_response(self, response: ClassificationAIResponse) -> None:
        if response.document_class not in DOCUMENT_CLASS_LABELS:
            raise ValueError(f"Classe documental inválida: {response.document_class}")
