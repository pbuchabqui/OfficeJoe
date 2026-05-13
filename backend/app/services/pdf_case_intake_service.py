from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Optional

import pdfplumber


CASE_NUMBER_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")


@dataclass(frozen=True)
class PDFCaseIntake:
    case_number: Optional[str]
    case_type: str
    title: str
    court: Optional[str]
    description: str
    extracted_text: str


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -:\t")


def _title_from_filename(filename: str) -> str:
    stem = Path(filename or "documento").stem.replace("_", " ").replace("-", " ")
    title = _clean_line(stem)
    return title[:500] or "Processo importado por PDF"


def _infer_case_type(text: str, filename: str) -> str:
    haystack = _strip_accents(f"{text} {filename}").lower()
    if any(term in haystack for term in ("trabalhista", "trabalho", "reclamante", "reclamado", "holerite", "salario")):
        return "trabalhista"
    if any(term in haystack for term in ("fiscal", "tributario", "tributaria", "imposto", "receita federal")):
        return "fiscal"
    if "arbitragem" in haystack or "arbitral" in haystack:
        return "arbitragem"
    if "extrajudicial" in haystack:
        return "extrajudicial"
    return "civel"


def _infer_court(lines: list[str]) -> Optional[str]:
    markers = ("vara", "tribunal", "justica", "juizo", "comarca")
    for line in lines[:40]:
        normalized = _strip_accents(line).lower()
        if any(marker in normalized for marker in markers):
            return line[:255]
    return None


def _infer_title(lines: list[str], filename: str, case_number: Optional[str]) -> str:
    ignored = {"poder judiciario", "processo judicial eletronico", "pje"}
    for line in lines[:50]:
        normalized = _strip_accents(line).lower()
        if case_number and case_number in line:
            continue
        if normalized in ignored or len(line) < 8:
            continue
        if any(marker in normalized for marker in ("vara", "tribunal", "justica", "juizo", "comarca")):
            continue
        return line[:500]
    return _title_from_filename(filename)


def _extract_text(stream: BinaryIO, max_pages: int = 3) -> str:
    pos = stream.tell() if hasattr(stream, "tell") else None
    try:
        stream.seek(0)
        chunks: list[str] = []
        with pdfplumber.open(stream) as pdf:
            for page in pdf.pages[:max_pages]:
                text = page.extract_text() or ""
                if text.strip():
                    chunks.append(text)
        return "\n".join(chunks)
    except Exception:
        return ""
    finally:
        if pos is not None:
            stream.seek(pos)


def inspect_pdf_for_case(stream: BinaryIO, filename: str) -> PDFCaseIntake:
    text = _extract_text(stream)
    lines = [_clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    match = CASE_NUMBER_RE.search(text)
    case_number = match.group(0) if match else None
    case_type = _infer_case_type(text, filename)
    court = _infer_court(lines)
    title = _infer_title(lines, filename, case_number)
    excerpt = _clean_line(" ".join(lines[:10]))

    description_parts = [
        "Processo criado automaticamente a partir do primeiro PDF anexado.",
        f"Arquivo original: {filename or 'documento.pdf'}.",
    ]
    if excerpt:
        description_parts.append(f"Trecho inicial extraido: {excerpt[:700]}")

    return PDFCaseIntake(
        case_number=case_number,
        case_type=case_type,
        title=title,
        court=court,
        description="\n".join(description_parts),
        extracted_text=text,
    )
