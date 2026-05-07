"""Initial timecard extractor from OCR text.

Pure, mockable module: no database, no storage, no labor calculations, no
exports. The public function receives OCR text and returns day rows with
per-field confidence and unreadable mark flags.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any


FieldPayload = dict[str, str | float | bool | None]


_DATE_RE = r"\b(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?|\d{4}-\d{2}-\d{2})\b"
_TIME_RE = r"\b(?:[01]?\d|2[0-3])[:hH.][0-5]\d\b"
_UNREADABLE_RE = re.compile(
    r"\b(?:ilegivel|illegivel|rasurado|borrado|cortado|falha|sem leitura|indecifravel|xxx+|---|\?\?\?)\b",
    flags=re.IGNORECASE,
)

_FIELD_ORDER = (
    "entrada_1",
    "saida_1",
    "entrada_2",
    "saida_2",
    "entrada_3",
    "saida_3",
    "entrada_4",
    "saida_4",
)


def extract_timecard_from_ocr_text(ocr_text: str) -> dict[str, Any]:
    """Extract initial timecard day rows from OCR text.

    This first version recognizes generic rows that start with a date/day and
    contain time marks. It preserves raw rows and marks low-quality or
    unreadable cells without calculating worked time or overtime.
    """
    text = _normalize_ocr_text(ocr_text)
    lines = _split_lines(text)
    days = _extract_days(lines)

    return {
        "days": days,
        "metadata": {
            "layout_variant": "generico",
            "layout_confidence": _layout_confidence(days),
            "source": "ocr_text",
        },
    }


def _extract_days(lines: list[str]) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    current_year = _infer_year(lines)
    current_month = _infer_month(lines)

    for line_index, line in enumerate(lines):
        parsed = _parse_day_line(line, line_index, current_month, current_year)
        if parsed is not None:
            days.append(parsed)

    return days


def _parse_day_line(
    line: str,
    line_index: int,
    current_month: int | None,
    current_year: int | None,
) -> dict[str, Any] | None:
    date_match = re.search(_DATE_RE, line)
    if not date_match:
        date_match = re.match(r"^\s*(\d{1,2})\b", line)
        if not date_match or current_month is None or current_year is None:
            return None

    raw_date = date_match.group(0)
    normalized_date = _normalize_date(raw_date, current_month, current_year)
    if normalized_date is None:
        return None

    row_after_date = line[date_match.end() :].strip()
    fields = _extract_time_fields(row_after_date)
    unreadable_notes = _extract_unreadable_notes(row_after_date)

    if not fields and not unreadable_notes:
        return None

    unreadable_count = sum(1 for field in fields.values() if field["is_unreadable"])
    if unreadable_notes and unreadable_count == 0:
        fields["observacao"] = _field(
            raw_value=unreadable_notes,
            normalized_value=None,
            confidence=0.45,
            is_unreadable=True,
            unreadable_note=unreadable_notes,
        )
        unreadable_count = 1

    return {
        "line_index": line_index,
        "date_raw": raw_date,
        "work_date": normalized_date.isoformat(),
        "weekday_label": _extract_weekday_label(row_after_date),
        "fields": fields,
        "raw_row": line,
        "confidence": _row_confidence(fields, unreadable_count),
        "unreadable_marks_count": unreadable_count,
        "unreadable_notes": unreadable_notes,
    }


def _extract_time_fields(row_text: str) -> dict[str, FieldPayload]:
    fields: dict[str, FieldPayload] = {}
    tokens = _extract_mark_tokens(row_text)
    has_time_token = any(_normalize_time(token) is not None for token in tokens)

    if tokens and not has_time_token:
        return {}

    order_index = 0
    for token in tokens:
        if order_index >= len(_FIELD_ORDER):
            break

        if _is_unreadable_token(token):
            field_name = _FIELD_ORDER[order_index]
            fields[field_name] = _field(
                raw_value=token,
                normalized_value=None,
                confidence=0.2,
                is_unreadable=True,
                unreadable_note="Marcacao ilegivel no OCR.",
            )
            order_index += 1
            continue

        normalized_time = _normalize_time(token)
        if normalized_time is None:
            continue

        field_name = _FIELD_ORDER[order_index]
        fields[field_name] = _field(
            raw_value=token,
            normalized_value=normalized_time,
            confidence=0.9 if ":" in token else 0.82,
            is_unreadable=False,
            unreadable_note=None,
        )
        order_index += 1

    return fields


def _extract_mark_tokens(row_text: str) -> list[str]:
    token_re = re.compile(
        rf"{_TIME_RE}|(?:xx+|---|\?\?\?|ilegivel|illegivel|rasurado|borrado|falha)",
        flags=re.IGNORECASE,
    )
    return [match.group(0) for match in token_re.finditer(row_text)]


def _extract_unreadable_notes(row_text: str) -> str | None:
    matches = [match.group(0) for match in _UNREADABLE_RE.finditer(row_text)]
    if not matches:
        return None
    unique = list(dict.fromkeys(matches))
    return "Marcacoes ilegiveis: " + ", ".join(unique)


def _extract_weekday_label(row_text: str) -> str | None:
    match = re.search(
        r"\b(seg|segunda|ter|terca|quarta|qua|quinta|qui|sexta|sex|sabado|sab|domingo|dom)\b",
        row_text,
        flags=re.IGNORECASE,
    )
    return match.group(0).lower() if match else None


def _normalize_ocr_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _normalize_time(value: str) -> str | None:
    match = re.fullmatch(r"([01]?\d|2[0-3])[:hH.]([0-5]\d)", value.strip())
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _normalize_date(value: str, current_month: int | None, current_year: int | None) -> date | None:
    value = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            year, month, day = (int(part) for part in value.split("-"))
            return date(year, month, day)

        parts = [int(part) for part in re.split(r"[/.-]", value)]
        if len(parts) == 3:
            day, month, year = parts
            if year < 100:
                year += 2000
            return date(year, month, day)

        if len(parts) == 2 and current_year is not None:
            day, month = parts
            return date(current_year, month, day)

        if len(parts) == 1 and current_month is not None and current_year is not None:
            return date(current_year, current_month, parts[0])
    except ValueError:
        return None

    return None


def _infer_year(lines: list[str]) -> int | None:
    for line in lines:
        match = re.search(r"\b(20\d{2}|19\d{2})\b", line)
        if match:
            return int(match.group(1))
    return None


def _infer_month(lines: list[str]) -> int | None:
    for line in lines:
        match = re.search(r"\b(?:competencia|referencia|periodo|mes)\b\s*[:\-]?\s*(0?[1-9]|1[0-2])[/.-]\d{4}", line, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))

    for line in lines:
        match = re.search(r"\b\d{1,2}[/.-](0?[1-9]|1[0-2])[/.-](?:20\d{2}|19\d{2})\b", line)
        if match:
            return int(match.group(1))

    return None


def _is_unreadable_token(value: str) -> bool:
    return _UNREADABLE_RE.search(value) is not None or value in {"---", "???", "xxx", "xxxx"}


def _row_confidence(fields: dict[str, FieldPayload], unreadable_count: int) -> float:
    if not fields:
        return 0.0

    confidences = [float(field["confidence"] or 0) for field in fields.values()]
    average = sum(confidences) / len(confidences)
    penalty = min(unreadable_count * 0.08, 0.24)
    return max(round(average - penalty, 2), 0.0)


def _layout_confidence(days: list[dict[str, Any]]) -> float:
    if not days:
        return 0.0

    rows_with_marks = sum(1 for day in days if day["fields"])
    score = rows_with_marks / len(days)
    if len(days) >= 3:
        score += 0.15
    return min(round(score, 2), 1.0)


def _field(
    raw_value: str,
    normalized_value: str | None,
    confidence: float,
    is_unreadable: bool,
    unreadable_note: str | None,
) -> FieldPayload:
    return {
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "confidence": confidence,
        "is_unreadable": is_unreadable,
        "unreadable_note": unreadable_note,
    }
