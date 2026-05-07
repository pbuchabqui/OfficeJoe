"""Extrator inicial de holerite a partir de texto OCR.

Modulo propositalmente puro: sem banco, sem storage, sem IA e sem chamadas
externas. A funcao publica recebe uma string OCR e retorna uma estrutura
serializavel com valor bruto, valor normalizado e confianca por campo.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


FieldPayload = dict[str, str | float | None]


_MONTHS = {
    "janeiro": "01",
    "fevereiro": "02",
    "marco": "03",
    "marco.": "03",
    "marco/": "03",
    "abril": "04",
    "maio": "05",
    "junho": "06",
    "julho": "07",
    "agosto": "08",
    "setembro": "09",
    "outubro": "10",
    "novembro": "11",
    "dezembro": "12",
}


def extract_holerite_from_ocr_text(ocr_text: str) -> dict[str, Any]:
    """Extrai campos estruturados de um texto OCR de holerite.

    O objetivo desta primeira versao e cobrir layouts genericos simulaveis:
    cabecalho com empregado/empresa, documentos, competencia e totais, alem de
    linhas simples de verbas. Campos ausentes simplesmente nao aparecem no
    resultado.
    """
    text = _normalize_ocr_text(ocr_text)
    lines = _split_lines(text)

    fields: dict[str, FieldPayload] = {}
    _put(fields, "cpf_empregado", _extract_cpf(text))
    _put(fields, "cnpj_empresa", _extract_cnpj(text))
    _put(fields, "competencia", _extract_competencia(text))
    _put(fields, "nome_empregado", _extract_labeled_text(lines, _EMPLOYEE_LABELS, confidence=0.86))
    _put(fields, "nome_empresa", _extract_labeled_text(lines, _COMPANY_LABELS, confidence=0.84))
    _put(fields, "matricula", _extract_labeled_value(text, _MATRICULA_LABELS, r"[A-Z0-9][A-Z0-9./-]{1,20}", 0.82))
    _put(fields, "salario_base", _extract_money_field(text, _SALARIO_BASE_LABELS, confidence=0.9))
    _put(fields, "total_proventos", _extract_money_field(text, _TOTAL_PROVENTOS_LABELS, confidence=0.92))
    _put(fields, "total_descontos", _extract_money_field(text, _TOTAL_DESCONTOS_LABELS, confidence=0.92))
    _put(fields, "salario_liquido", _extract_money_field(text, _SALARIO_LIQUIDO_LABELS, confidence=0.93))

    verbas = _extract_verbas(lines)
    math_check = _build_math_check(fields)

    return {
        "fields": fields,
        "verbas": verbas,
        "math_check": math_check,
        "metadata": {
            "layout_variant": "generico",
            "layout_confidence": _layout_confidence(fields, verbas),
            "source": "ocr_text",
        },
    }


_EMPLOYEE_LABELS = (
    "empregado",
    "funcionario",
    "colaborador",
    "nome do empregado",
    "nome funcionario",
)
_COMPANY_LABELS = ("empresa", "empregador", "razao social")
_MATRICULA_LABELS = ("matricula", "registro")
_SALARIO_BASE_LABELS = ("salario base", "sal. base", "salario contratual")
_TOTAL_PROVENTOS_LABELS = ("total de proventos", "total proventos", "proventos")
_TOTAL_DESCONTOS_LABELS = ("total de descontos", "total descontos", "descontos")
_SALARIO_LIQUIDO_LABELS = ("liquido a receber", "valor liquido", "salario liquido", "liquido")

_MONEY_RE = r"(?:R\$\s*)?-?\d{1,3}(?:\.\d{3})*,\d{2}|(?:R\$\s*)?-?\d+,\d{2}"


def _put(fields: dict[str, FieldPayload], key: str, payload: FieldPayload | None) -> None:
    if payload is not None:
        fields[key] = payload


def _normalize_ocr_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _extract_cpf(text: str) -> FieldPayload | None:
    match = re.search(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}\b", text)
    if not match:
        return None
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 11:
        return None
    return _field(raw, f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}", 0.94)


def _extract_cnpj(text: str) -> FieldPayload | None:
    match = re.search(r"\b\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}\b", text)
    if not match:
        return None
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 14:
        return None
    normalized = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return _field(raw, normalized, 0.94)


def _extract_competencia(text: str) -> FieldPayload | None:
    labeled = _extract_labeled_value(
        text,
        ("competencia", "referencia", "mes ano", "mes/ano"),
        r"(?:0?[1-9]|1[0-2])[/.-]\d{4}",
        0.9,
    )
    if labeled:
        normalized = _normalize_competencia(str(labeled["raw_value"]))
        if normalized:
            labeled["normalized_value"] = normalized
            return labeled

    month_name = re.search(
        r"\b(janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s*/?\s*(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    if not month_name:
        return None
    month = _strip_accents(month_name.group(1).lower())
    normalized = f"{_MONTHS[month]}/{month_name.group(2)}"
    return _field(month_name.group(0), normalized, 0.84)


def _extract_labeled_text(lines: list[str], labels: tuple[str, ...], confidence: float) -> FieldPayload | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    for line in lines:
        match = re.search(rf"\b(?:{label_pattern})\b\s*[:\-]?\s*(.+)$", line, flags=re.IGNORECASE)
        if not match:
            continue
        value = _clean_text_value(match.group(1))
        if value and not _looks_like_money(value):
            return _field(value, value.upper(), confidence)
    return None


def _extract_labeled_value(
    text: str,
    labels: tuple[str, ...],
    value_pattern: str,
    confidence: float,
) -> FieldPayload | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"\b(?:{label_pattern})\b\s*[:\-]?\s*({value_pattern})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    raw = _clean_text_value(match.group(1))
    return _field(raw, raw, confidence)


def _extract_money_field(text: str, labels: tuple[str, ...], confidence: float) -> FieldPayload | None:
    payload = _extract_labeled_value(text, labels, _MONEY_RE, confidence)
    if not payload:
        return None
    normalized = _normalize_money(str(payload["raw_value"]))
    if normalized is None:
        return None
    payload["normalized_value"] = normalized
    return payload


def _extract_verbas(lines: list[str]) -> list[dict[str, Any]]:
    verbas: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        parsed = _parse_verba_line(line, index)
        if parsed:
            verbas.append(parsed)
    return verbas


def _parse_verba_line(line: str, index: int) -> dict[str, Any] | None:
    if not re.match(r"^\d{2,5}\s+", line):
        return None
    if re.search(r"\b(total|liquido|base fgts|base inss)\b", line, flags=re.IGNORECASE):
        return None

    money_values = list(re.finditer(_MONEY_RE, line, flags=re.IGNORECASE))
    if not money_values:
        return None

    code_match = re.match(r"^(?P<codigo>\d{2,5})\s+(?P<rest>.+)$", line)
    if not code_match:
        return None

    last_money = money_values[-1]
    raw_value = last_money.group(0)
    value_decimal = _normalize_money(raw_value)
    before_value = line[len(code_match.group("codigo")):last_money.start()].strip()
    after_value = line[last_money.end():].strip()
    tipo = _infer_verba_tipo(line, after_value)

    reference_match = re.search(r"(\d+(?:[,.]\d{1,2})?%?|\d{1,3}:\d{2})\s*$", before_value)
    referencia = reference_match.group(1) if reference_match else None
    descricao = before_value[: reference_match.start()].strip() if reference_match else before_value
    descricao = re.sub(r"\s{2,}", " ", descricao).strip(" -")

    if not descricao:
        return None

    return {
        "line_index": index,
        "codigo": code_match.group("codigo"),
        "descricao": descricao,
        "referencia": referencia,
        "valor_raw": raw_value,
        "valor_decimal": value_decimal,
        "tipo": tipo,
        "raw_row": line,
        "confidence": 0.78 if tipo != "informativo" else 0.68,
    }


def _infer_verba_tipo(line: str, suffix: str) -> str:
    haystack = f"{line} {suffix}".lower()
    if re.search(r"\b(desc|desconto|inss|irrf|faltas?|vale|adiantamento)\b", haystack):
        return "desconto"
    if re.search(r"\b(info|informativo|base)\b", haystack):
        return "informativo"
    return "provento"


def _build_math_check(fields: dict[str, FieldPayload]) -> dict[str, Any]:
    proventos = _decimal_from_field(fields.get("total_proventos"))
    descontos = _decimal_from_field(fields.get("total_descontos"))
    liquido = _decimal_from_field(fields.get("salario_liquido"))
    if proventos is None or descontos is None or liquido is None:
        return {"passed": None, "delta": None, "confidence": 0.0}

    expected = proventos - descontos
    delta = expected - liquido
    passed = abs(delta) <= Decimal("0.01")
    return {
        "passed": passed,
        "delta": f"{delta:.2f}",
        "confidence": 0.9 if passed else 0.55,
    }


def _decimal_from_field(field: FieldPayload | None) -> Decimal | None:
    if not field or field.get("normalized_value") is None:
        return None
    try:
        return Decimal(str(field["normalized_value"]))
    except InvalidOperation:
        return None


def _layout_confidence(fields: dict[str, FieldPayload], verbas: list[dict[str, Any]]) -> float:
    anchors = {"cpf_empregado", "competencia", "total_proventos", "total_descontos", "salario_liquido"}
    score = sum(1 for key in anchors if key in fields) / len(anchors)
    if verbas:
        score += 0.15
    return min(round(score, 2), 1.0)


def _field(raw_value: str, normalized_value: str | None, confidence: float) -> FieldPayload:
    return {
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "confidence": confidence,
    }


def _normalize_competencia(value: str) -> str | None:
    match = re.search(r"(0?[1-9]|1[0-2])[/.-](\d{4})", value)
    if not match:
        return None
    return f"{int(match.group(1)):02d}/{match.group(2)}"


def _normalize_money(value: str) -> str | None:
    cleaned = value.replace("R$", "").replace(" ", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        parsed = Decimal(cleaned)
    except InvalidOperation:
        return None
    return f"{parsed:.2f}"


def _clean_text_value(value: str) -> str:
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip(" :;-")


def _looks_like_money(value: str) -> bool:
    return re.fullmatch(_MONEY_RE, value, flags=re.IGNORECASE) is not None


def _strip_accents(value: str) -> str:
    return (
        value.replace("ç", "c")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("ú", "u")
    )
