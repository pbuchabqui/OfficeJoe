from __future__ import annotations

from app.services.holerite_ocr_extractor import extract_holerite_from_ocr_text


def test_extracts_structured_fields_with_confidence_from_simulated_ocr():
    text = """
    DEMONSTRATIVO DE PAGAMENTO
    Empresa: ACME INDUSTRIA LTDA
    CNPJ: 12.345.678/0001-90
    Empregado: JOSE DA SILVA
    CPF: 123.456.789-09
    Matricula: A1020
    Competencia: 05/2024

    001 Salario Base 30,00 3.500,00 PROVENTO
    101 INSS 9,00 315,00 DESCONTO
    102 IRRF 7,50 120,00 DESCONTO

    Salario Base: R$ 3.500,00
    Total de Proventos: R$ 3.500,00
    Total de Descontos: R$ 435,00
    Liquido a Receber: R$ 3.065,00
    """

    result = extract_holerite_from_ocr_text(text)

    fields = result["fields"]
    assert fields["nome_empresa"]["normalized_value"] == "ACME INDUSTRIA LTDA"
    assert fields["nome_empregado"]["normalized_value"] == "JOSE DA SILVA"
    assert fields["cpf_empregado"]["normalized_value"] == "123.456.789-09"
    assert fields["cnpj_empresa"]["normalized_value"] == "12.345.678/0001-90"
    assert fields["competencia"]["normalized_value"] == "05/2024"
    assert fields["salario_liquido"]["normalized_value"] == "3065.00"
    assert fields["salario_liquido"]["confidence"] > 0.9
    assert result["math_check"]["passed"] is True
    assert result["math_check"]["delta"] == "0.00"


def test_extracts_verbas_from_simple_payroll_rows():
    text = """
    Funcionario: MARIA SOUZA
    CPF 98765432100
    Referencia 11-2023

    001 SALARIO MENSAL 30,00 2800,00
    050 HORAS EXTRAS 50% 420,00
    201 INSS 9,00 252,00
    202 VALE TRANSPORTE 6,00 168,00

    Total Proventos 3.220,00
    Total Descontos 420,00
    Valor Liquido 2.800,00
    """

    result = extract_holerite_from_ocr_text(text)

    assert result["fields"]["competencia"]["normalized_value"] == "11/2023"
    assert result["fields"]["cpf_empregado"]["normalized_value"] == "987.654.321-00"
    assert result["math_check"]["passed"] is True

    verbas = result["verbas"]
    assert len(verbas) == 4
    assert verbas[0]["codigo"] == "001"
    assert verbas[0]["descricao"] == "SALARIO MENSAL"
    assert verbas[0]["valor_decimal"] == "2800.00"
    assert verbas[0]["tipo"] == "provento"
    assert verbas[2]["tipo"] == "desconto"
    assert verbas[3]["tipo"] == "desconto"
    assert all(verba["confidence"] > 0 for verba in verbas)


def test_accepts_month_name_competencia_and_missing_totals():
    text = """
    HOLERITE
    Empregador - BETA SERVICOS
    Colaborador: ANA PEREIRA
    CPF: 111.222.333-44
    Maio/2024
    """

    result = extract_holerite_from_ocr_text(text)

    assert result["fields"]["competencia"]["normalized_value"] == "05/2024"
    assert result["fields"]["nome_empresa"]["normalized_value"] == "BETA SERVICOS"
    assert result["fields"]["nome_empregado"]["normalized_value"] == "ANA PEREIRA"
    assert "total_proventos" not in result["fields"]
    assert result["math_check"]["passed"] is None
    assert result["metadata"]["layout_variant"] == "generico"


def test_empty_ocr_text_returns_empty_fields_and_no_math_check():
    result = extract_holerite_from_ocr_text("")

    assert result["fields"] == {}
    assert result["verbas"] == []
    assert result["math_check"] == {"passed": None, "delta": None, "confidence": 0.0}
    assert result["metadata"]["layout_confidence"] == 0.0
