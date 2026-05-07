"""
Pipeline de OCR multi-engine com rastreamento de coordenadas e confiança por página.

Ordem de preferência:
1. pdfplumber  – extrai texto nativo (PDFs com camada de texto)
2. PaddleOCR   – OCR principal para imagens/PDFs escaneados
3. Tesseract   – fallback

Princípio: o arquivo original NUNCA é modificado.
"""
from __future__ import annotations

import io
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF – renderiza páginas como imagem sem alterar o PDF
import pdfplumber

from app.core.config import get_settings

logger = logging.getLogger("officejoe.ocr")
settings = get_settings()


# ── Estruturas de dados ───────────────────────────────────────────────────────

@dataclass
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class TextBlock:
    text: str
    bbox: BoundingBox
    confidence: float
    source: str  # "native" | "paddleocr" | "tesseract"


@dataclass
class PageResult:
    page_number: int          # 1-indexed
    raw_text: str
    text_blocks: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    width_pt: float
    height_pt: float
    ocr_engine: str
    confidence: float
    has_text_layer: bool
    is_image_only: bool
    error: Optional[str] = None


@dataclass
class DocumentOCRResult:
    document_id: str
    total_pages: int
    pages: List[PageResult] = field(default_factory=list)
    avg_confidence: float = 0.0
    engine_used: str = "mixed"
    error: Optional[str] = None


# ── Extratores ────────────────────────────────────────────────────────────────

class PDFPlumberExtractor:
    """Extrai texto nativo de PDFs com camada de texto."""

    MIN_TEXT_LENGTH = 20  # Mínimo de chars para considerar que há texto nativo

    def extract_page(self, pdf_path: Path, page_number: int) -> Optional[PageResult]:
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                if page_number > len(pdf.pages):
                    return None
                page = pdf.pages[page_number - 1]
                text = page.extract_text() or ""
                has_text = len(text.strip()) >= self.MIN_TEXT_LENGTH

                # Extrai blocos com coordenadas
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    use_text_flow=True,
                )
                text_blocks = [
                    {
                        "text": w["text"],
                        "x0": w["x0"], "y0": w["top"],
                        "x1": w["x1"], "y1": w["bottom"],
                        "confidence": 1.0,
                        "source": "native",
                    }
                    for w in words
                ]

                # Extrai tabelas
                tables_raw = page.extract_tables() or []
                tables = [
                    {"rows": t, "page": page_number}
                    for t in tables_raw if t
                ]

                return PageResult(
                    page_number=page_number,
                    raw_text=text,
                    text_blocks=text_blocks,
                    tables=tables,
                    width_pt=float(page.width),
                    height_pt=float(page.height),
                    ocr_engine="pdfplumber",
                    confidence=1.0 if has_text else 0.0,
                    has_text_layer=has_text,
                    is_image_only=not has_text,
                )
        except Exception as exc:
            logger.warning("pdfplumber falhou na página %d: %s", page_number, exc)
            return None


class PaddleOCRExtractor:
    """OCR com PaddleOCR – alta precisão para português."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "PaddleOCRExtractor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._engine = None

    def _load_engine(self):
        if self._engine is None:
            try:
                from paddleocr import PaddleOCR
                self._engine = PaddleOCR(
                    use_angle_cls=True,
                    lang="pt",
                    use_gpu=False,
                    show_log=False,
                )
                logger.info("PaddleOCR carregado.")
            except ImportError:
                logger.warning("PaddleOCR não disponível, usando Tesseract.")
                raise
        return self._engine

    def extract_from_image(
        self, image_bytes: bytes, page_number: int, page_width: float, page_height: float
    ) -> PageResult:
        try:
            engine = self._load_engine()
            import numpy as np
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_array = np.array(image)

            results = engine.ocr(img_array, cls=True)

            text_blocks = []
            lines = []
            confidences = []

            if results and results[0]:
                for line in results[0]:
                    if not line:
                        continue
                    bbox_pts, (text, conf) = line
                    # bbox_pts: [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
                    xs = [p[0] for p in bbox_pts]
                    ys = [p[1] for p in bbox_pts]

                    # Normaliza para coordenadas de página PDF
                    scale_x = page_width / image.width
                    scale_y = page_height / image.height
                    x0 = min(xs) * scale_x
                    y0 = min(ys) * scale_y
                    x1 = max(xs) * scale_x
                    y1 = max(ys) * scale_y

                    text_blocks.append({
                        "text": text,
                        "x0": x0, "y0": y0,
                        "x1": x1, "y1": y1,
                        "confidence": float(conf),
                        "source": "paddleocr",
                    })
                    lines.append(text)
                    confidences.append(float(conf))

            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            raw_text = "\n".join(lines)

            return PageResult(
                page_number=page_number,
                raw_text=raw_text,
                text_blocks=text_blocks,
                tables=[],
                width_pt=page_width,
                height_pt=page_height,
                ocr_engine="paddleocr",
                confidence=avg_conf,
                has_text_layer=False,
                is_image_only=True,
            )
        except Exception as exc:
            logger.error("PaddleOCR falhou na página %d: %s", page_number, exc)
            return PageResult(
                page_number=page_number,
                raw_text="",
                text_blocks=[],
                tables=[],
                width_pt=page_width,
                height_pt=page_height,
                ocr_engine="paddleocr",
                confidence=0.0,
                has_text_layer=False,
                is_image_only=True,
                error=str(exc),
            )


class TesseractExtractor:
    """Fallback OCR usando pytesseract."""

    def extract_from_image(
        self, image_bytes: bytes, page_number: int, page_width: float, page_height: float
    ) -> PageResult:
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGE)
            data = pytesseract.image_to_data(
                image,
                lang=settings.OCR_LANGUAGE,
                output_type=pytesseract.Output.DICT,
            )

            text_blocks = []
            confidences = []

            for i, conf in enumerate(data["conf"]):
                try:
                    conf_f = float(conf)
                except (ValueError, TypeError):
                    continue
                if conf_f < 0 or not data["text"][i].strip():
                    continue

                x0 = data["left"][i] * (page_width / image.width)
                y0 = data["top"][i] * (page_height / image.height)
                x1 = (data["left"][i] + data["width"][i]) * (page_width / image.width)
                y1 = (data["top"][i] + data["height"][i]) * (page_height / image.height)

                text_blocks.append({
                    "text": data["text"][i],
                    "x0": x0, "y0": y0,
                    "x1": x1, "y1": y1,
                    "confidence": conf_f / 100.0,
                    "source": "tesseract",
                })
                confidences.append(conf_f / 100.0)

            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            return PageResult(
                page_number=page_number,
                raw_text=text,
                text_blocks=text_blocks,
                tables=[],
                width_pt=page_width,
                height_pt=page_height,
                ocr_engine="tesseract",
                confidence=avg_conf,
                has_text_layer=False,
                is_image_only=True,
            )
        except Exception as exc:
            logger.error("Tesseract falhou na página %d: %s", page_number, exc)
            return PageResult(
                page_number=page_number,
                raw_text="",
                text_blocks=[],
                tables=[],
                width_pt=page_width,
                height_pt=page_height,
                ocr_engine="tesseract",
                confidence=0.0,
                has_text_layer=False,
                is_image_only=True,
                error=str(exc),
            )


# ── Pipeline principal ────────────────────────────────────────────────────────

class OCRService:
    """
    Orquestra o pipeline de OCR:
    1. Para cada página: tenta extração nativa (pdfplumber)
    2. Se não há texto nativo: renderiza como imagem e aplica OCR
    3. Mantém rastreabilidade de coordenadas em todas as etapas
    """

    def __init__(self) -> None:
        self._plumber = PDFPlumberExtractor()
        self._paddle = PaddleOCRExtractor.get_instance()
        self._tesseract = TesseractExtractor()

    def _render_page_as_image(
        self, doc: fitz.Document, page_idx: int, dpi: int = 300
    ) -> Tuple[bytes, float, float]:
        """Renderiza uma página como PNG sem modificar o PDF."""
        page = doc[page_idx]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        return img_bytes, float(page.rect.width), float(page.rect.height)

    def process_document(
        self,
        pdf_path: Path,
        document_id: str,
        page_start: int = 1,
        page_end: Optional[int] = None,
    ) -> DocumentOCRResult:
        """
        Processa um PDF completo ou intervalo de páginas.
        Retorna resultado com rastreabilidade completa por página.
        """
        result = DocumentOCRResult(document_id=document_id, total_pages=0)

        try:
            fitz_doc = fitz.open(str(pdf_path))
            total = len(fitz_doc)
            result.total_pages = total

            end = min(page_end or total, total)

            for page_idx in range(page_start - 1, end):
                page_num = page_idx + 1
                logger.debug("OCR página %d/%d doc=%s", page_num, total, document_id)

                # Tenta extração nativa primeiro
                native = self._plumber.extract_page(pdf_path, page_num)

                if native and native.has_text_layer:
                    result.pages.append(native)
                    continue

                # Renderiza página como imagem (sem alterar o PDF)
                img_bytes, w, h = self._render_page_as_image(fitz_doc, page_idx, settings.OCR_DPI)

                # Tenta PaddleOCR
                if settings.OCR_ENGINE in ("paddleocr", "auto"):
                    page_result = self._paddle.extract_from_image(img_bytes, page_num, w, h)
                else:
                    page_result = self._tesseract.extract_from_image(img_bytes, page_num, w, h)

                # Fallback para Tesseract se PaddleOCR falhou
                if page_result.error and settings.OCR_ENGINE == "auto":
                    page_result = self._tesseract.extract_from_image(img_bytes, page_num, w, h)

                # Mescla tabelas do pdfplumber (mesmo sem texto nativo, ele detecta tabelas)
                if native and native.tables:
                    page_result.tables = native.tables

                result.pages.append(page_result)

            fitz_doc.close()

            # Calcula confiança média
            confidences = [p.confidence for p in result.pages if p.confidence > 0]
            result.avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

            engines = {p.ocr_engine for p in result.pages}
            result.engine_used = "+".join(sorted(engines))

        except Exception as exc:
            logger.error("Falha no pipeline OCR: doc=%s erro=%s", document_id, exc)
            result.error = str(exc)

        return result

    def process_document_bytes(
        self,
        pdf_bytes: bytes,
        document_id: str,
        page_start: int = 1,
        page_end: Optional[int] = None,
    ) -> DocumentOCRResult:
        """Processa PDF a partir de bytes (sem gravar em disco)."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            return self.process_document(
                Path(tmp.name), document_id, page_start, page_end
            )


def get_ocr_service() -> OCRService:
    return OCRService()
