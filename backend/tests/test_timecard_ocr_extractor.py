from __future__ import annotations

from app.services.timecard_ocr_extractor import extract_timecard_from_ocr_text


def test_extracts_day_rows_and_time_fields_from_simulated_ocr():
    text = """
    CARTAO PONTO
    Competencia: 05/2024
    Empregado: JOSE DA SILVA

    01/05/2024 qua 08:00 12:00 13:00 17:48
    02/05/2024 qui 08h05 12h01 13h02 17h55
    03/05/2024 sex 07.58 12.00 13.00 17.45
    """

    result = extract_timecard_from_ocr_text(text)

    assert result["metadata"]["layout_variant"] == "generico"
    assert result["metadata"]["layout_confidence"] == 1.0

    days = result["days"]
    assert len(days) == 3
    assert days[0]["work_date"] == "2024-05-01"
    assert days[0]["weekday_label"] == "qua"
    assert days[0]["fields"]["entrada_1"]["normalized_value"] == "08:00"
    assert days[0]["fields"]["saida_1"]["normalized_value"] == "12:00"
    assert days[0]["fields"]["entrada_2"]["normalized_value"] == "13:00"
    assert days[0]["fields"]["saida_2"]["normalized_value"] == "17:48"
    assert days[0]["fields"]["entrada_1"]["confidence"] > 0.8
    assert days[0]["unreadable_marks_count"] == 0

    assert days[1]["fields"]["entrada_1"]["raw_value"] == "08h05"
    assert days[1]["fields"]["entrada_1"]["normalized_value"] == "08:05"
    assert days[2]["fields"]["entrada_1"]["raw_value"] == "07.58"
    assert days[2]["fields"]["entrada_1"]["normalized_value"] == "07:58"


def test_marks_unreadable_fields_with_confidence_and_notes():
    text = """
    Periodo: 06/2024
    10 seg 08:01 ilegivel 13:00 18:00
    11 ter 08:00 12:00 ??? 17:50
    12 qua rasurado
    """

    result = extract_timecard_from_ocr_text(text)

    days = result["days"]
    assert len(days) == 3

    first = days[0]
    assert first["work_date"] == "2024-06-10"
    assert first["fields"]["entrada_1"]["normalized_value"] == "08:01"
    assert first["fields"]["saida_1"]["is_unreadable"] is True
    assert first["fields"]["saida_1"]["normalized_value"] is None
    assert first["fields"]["saida_1"]["confidence"] < 0.5
    assert first["unreadable_marks_count"] == 1
    assert "Marcacoes ilegiveis" in first["unreadable_notes"]

    second = days[1]
    assert second["fields"]["entrada_2"]["is_unreadable"] is True
    assert second["fields"]["saida_2"]["normalized_value"] == "17:50"

    third = days[2]
    assert third["fields"]["observacao"]["is_unreadable"] is True
    assert third["unreadable_marks_count"] == 1


def test_ignores_lines_without_date_or_marks():
    text = """
    CARTAO PONTO
    Nome: MARIA SOUZA
    Departamento: Producao
    Assinatura do empregado
    """

    result = extract_timecard_from_ocr_text(text)

    assert result["days"] == []
    assert result["metadata"]["layout_confidence"] == 0.0


def test_empty_ocr_text_returns_empty_days():
    result = extract_timecard_from_ocr_text("")

    assert result == {
        "days": [],
        "metadata": {
            "layout_variant": "generico",
            "layout_confidence": 0.0,
            "source": "ocr_text",
        },
    }
