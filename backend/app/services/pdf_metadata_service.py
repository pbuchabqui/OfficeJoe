"""
Extração inicial e leve de metadados de PDF.
Não altera o arquivo original; apenas lê o stream recebido.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional

import pdfplumber


@dataclass(frozen=True)
class PDFMetadata:
    total_pages: Optional[int]
    file_size_bytes: int
    pdf_is_valid: bool
    has_native_text: Optional[bool]


def extract_pdf_metadata(stream: io.IOBase, file_size_bytes: int) -> PDFMetadata:
    """
    Lê metadados básicos do PDF a partir de um stream seekable.
    A detecção de texto nativo é propositalmente simples: tenta extrair texto
    das primeiras páginas até encontrar conteúdo textual.
    """
    pos = stream.tell() if hasattr(stream, "tell") else None
    try:
        stream.seek(0)
        with pdfplumber.open(stream) as pdf:
            has_text = False
            for page in pdf.pages[:3]:
                text = page.extract_text() or ""
                if text.strip():
                    has_text = True
                    break
            return PDFMetadata(
                total_pages=len(pdf.pages),
                file_size_bytes=file_size_bytes,
                pdf_is_valid=True,
                has_native_text=has_text,
            )
    except Exception:
        return PDFMetadata(
            total_pages=None,
            file_size_bytes=file_size_bytes,
            pdf_is_valid=False,
            has_native_text=None,
        )
    finally:
        if pos is not None:
            stream.seek(pos)
