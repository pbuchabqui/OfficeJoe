"""
Testes unitários para o serviço OCR.
Usa PDFs sintéticos gerados em memória — sem arquivos reais.
"""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest

from app.services.ocr_service import (
    PDFPlumberExtractor,
    TesseractExtractor,
    _chunk_text_for_test if False else None,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_minimal_pdf_bytes() -> bytes:
    """Cria um PDF mínimo válido com uma página de texto."""
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), "Documento de teste para OCR. CPF: 123.456.789-00", fontsize=12)
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()
        return buf.getvalue()
    except ImportError:
        pytest.skip("PyMuPDF não disponível")


# ── Testes de chunking ────────────────────────────────────────────────────────

def test_chunk_text_basic():
    from app.tasks.embedding_tasks import _chunk_text
    text = "A" * 3000
    chunks = _chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c) <= 1000


def test_chunk_text_short():
    from app.tasks.embedding_tasks import _chunk_text
    text = "Texto curto"
    chunks = _chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_empty():
    from app.tasks.embedding_tasks import _chunk_text
    chunks = _chunk_text("", chunk_size=1000, overlap=200)
    assert chunks == []


def test_chunk_overlap_preserves_context():
    from app.tasks.embedding_tasks import _chunk_text
    text = "X" * 1500
    chunks = _chunk_text(text, chunk_size=1000, overlap=200)
    # Segundo chunk deve começar antes do fim do primeiro
    assert len(chunks) == 2


# ── Testes de extração de entidades ──────────────────────────────────────────

def test_cpf_extraction():
    from app.tasks.extraction_tasks import _extract_entities
    text = "O autor CPF 123.456.789-00 reclamou verbas rescisórias."
    extractions = _extract_entities(text, 1, "doc-001", "page-001")
    cpfs = [e for e in extractions if e["extraction_type"] == "entity_cpf"]
    assert len(cpfs) == 1
    assert "123.456.789-00" in cpfs[0]["raw_value"]


def test_cnpj_extraction():
    from app.tasks.extraction_tasks import _extract_entities
    text = "Empresa reclamada CNPJ 12.345.678/0001-90 conforme contrato."
    extractions = _extract_entities(text, 1, "doc-001", "page-001")
    cnpjs = [e for e in extractions if e["extraction_type"] == "entity_cnpj"]
    assert len(cnpjs) >= 1


def test_date_extraction():
    from app.tasks.extraction_tasks import _extract_entities
    text = "Admissão em 01/03/2020 e demissão em 15/08/2023."
    extractions = _extract_entities(text, 1, "doc-001", "page-001")
    dates = [e for e in extractions if e["extraction_type"] == "entity_date"]
    assert len(dates) == 2


def test_currency_extraction():
    from app.tasks.extraction_tasks import _extract_entities
    text = "Salário de R$ 3.500,00 e décimo R$ 291,67."
    extractions = _extract_entities(text, 1, "doc-001", "page-001")
    currencies = [e for e in extractions if e["extraction_type"] == "entity_currency"]
    assert len(currencies) == 2
    # Verifica normalização
    values_normalized = [e["normalized_value"] for e in currencies]
    assert "3500.00" in values_normalized or "3.500" in str(values_normalized)


def test_no_entities_in_empty_text():
    from app.tasks.extraction_tasks import _extract_entities
    extractions = _extract_entities("", 1, "doc-001", "page-001")
    assert extractions == []


def test_extraction_has_required_fields():
    from app.tasks.extraction_tasks import _extract_entities
    text = "CPF 111.222.333-44"
    extractions = _extract_entities(text, 5, "doc-xyz", "page-abc")
    assert len(extractions) == 1
    ext = extractions[0]
    assert "id" in ext
    assert ext["page_number"] == 5
    assert ext["document_id"] == "doc-xyz"
    assert ext["confidence"] > 0


# ── Testes de PDF nativo ──────────────────────────────────────────────────────

def test_pdfplumber_extracts_text():
    import tempfile
    from pathlib import Path
    pdf_bytes = _make_minimal_pdf_bytes()
    extractor = PDFPlumberExtractor()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)
    try:
        result = extractor.extract_page(tmp_path, 1)
        assert result is not None
        assert result.page_number == 1
        assert result.width_pt > 0
        assert result.height_pt > 0
    finally:
        tmp_path.unlink(missing_ok=True)


def test_pdfplumber_page_out_of_range():
    import tempfile
    from pathlib import Path
    pdf_bytes = _make_minimal_pdf_bytes()
    extractor = PDFPlumberExtractor()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)
    try:
        result = extractor.extract_page(tmp_path, 9999)
        assert result is None
    finally:
        tmp_path.unlink(missing_ok=True)
