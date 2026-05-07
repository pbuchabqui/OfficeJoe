/**
 * Hook com dados mockados do painel lateral por página.
 * Em produção, seria substituído por chamadas à API real.
 */

import { useMemo } from 'react';
import { PageSidebarData } from '../types/sidebar';

const MOCK_DATA: Record<number, PageSidebarData> = {
  1: {
    pageNumber: 1,
    classification: {
      documentClass: 'petição inicial',
      confidence: 0.97,
      provider: 'anthropic',
      modelName: 'claude-sonnet-4-6',
    },
    validation: { status: 'validated', validatedBy: 'Dr. Souza', validatedAt: '2024-11-05T14:30:00Z' },
    ocr: {
      fullText:
        'EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA VARA DO TRABALHO\n\n' +
        'JOÃO DA SILVA, brasileiro, solteiro, empregado, portador do RG n.º 12.345.678-9 ' +
        'e CPF n.º 123.456.789-00, residente e domiciliado na Rua das Flores, n.º 100, ' +
        'São Paulo/SP, CEP 01001-000, vem respeitosamente à presença de Vossa Excelência ' +
        'propor RECLAMAÇÃO TRABALHISTA em face de EMPRESA XYZ LTDA.',
      averageConfidence: 0.95,
      hasLowConfidence: false,
      blocks: [
        { text: 'EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA VARA DO TRABALHO', confidence: 0.98, lowConfidence: false },
        { text: 'JOÃO DA SILVA, brasileiro, solteiro, empregado, portador do RG n.º 12.345.678-9', confidence: 0.96, lowConfidence: false },
        { text: 'propor RECLAMAÇÃO TRABALHISTA em face de EMPRESA XYZ LTDA.', confidence: 0.94, lowConfidence: false },
      ],
    },
    inventoryItem: {
      id: 'inv-001',
      documentClass: 'petição inicial',
      startPage: 1,
      endPage: 3,
      pageCount: 3,
      customLabel: null,
      isRelevant: true,
    },
  },
  2: {
    pageNumber: 2,
    classification: {
      documentClass: 'petição inicial',
      confidence: 0.91,
      provider: 'anthropic',
      modelName: 'claude-sonnet-4-6',
    },
    validation: { status: 'not_validated' },
    ocr: {
      fullText:
        'DOS FATOS\n\nO reclamante foi admitido em 05/01/2020 no cargo de Auxiliar Administrativo, ' +
        'percebendo salário mensal de R$ 2.500,00. Ocorre que a empresa deixou de pagar as verbas ' +
        'rescisórias devidas, sendo que o saldo devedor importa em R$ 8.432,16 (oito mil, ' +
        'quatrocentos e trinta e dois reais e dezesseis centavos).',
      averageConfidence: 0.88,
      hasLowConfidence: true,
      blocks: [
        { text: 'DOS FATOS', confidence: 0.99, lowConfidence: false },
        { text: 'O reclamante foi admitido em 05/01/2020 no cargo de Auxiliar Administrativo,', confidence: 0.92, lowConfidence: false },
        { text: 'percebendo salário mensal de R$ 2.500,00.', confidence: 0.75, lowConfidence: true },
        { text: 'sendo que o saldo devedor importa em R$ 8.432,16', confidence: 0.71, lowConfidence: true },
      ],
    },
    inventoryItem: {
      id: 'inv-001',
      documentClass: 'petição inicial',
      startPage: 1,
      endPage: 3,
      pageCount: 3,
      customLabel: null,
      isRelevant: true,
    },
  },
  3: {
    pageNumber: 3,
    classification: {
      documentClass: 'petição inicial',
      confidence: 0.89,
      provider: 'anthropic',
      modelName: 'claude-sonnet-4-6',
    },
    validation: { status: 'not_validated' },
    ocr: {
      fullText:
        'DOS PEDIDOS\n\nDiante do exposto, requer seja a presente reclamação julgada PROCEDENTE ' +
        'para condenar a reclamada ao pagamento de:\n\n' +
        'a) Saldo de salário: R$ 1.250,00\n' +
        'b) 13º salário proporcional: R$ 833,33\n' +
        'c) Férias + 1/3: R$ 1.111,11\n' +
        'd) FGTS + multa 40%: R$ 5.237,72',
      averageConfidence: 0.94,
      hasLowConfidence: false,
      blocks: [
        { text: 'DOS PEDIDOS', confidence: 0.99, lowConfidence: false },
        { text: 'a) Saldo de salário: R$ 1.250,00', confidence: 0.97, lowConfidence: false },
        { text: 'b) 13º salário proporcional: R$ 833,33', confidence: 0.93, lowConfidence: false },
        { text: 'c) Férias + 1/3: R$ 1.111,11', confidence: 0.90, lowConfidence: false },
        { text: 'd) FGTS + multa 40%: R$ 5.237,72', confidence: 0.95, lowConfidence: false },
      ],
    },
    inventoryItem: {
      id: 'inv-001',
      documentClass: 'petição inicial',
      startPage: 1,
      endPage: 3,
      pageCount: 3,
      customLabel: null,
      isRelevant: true,
    },
  },
  4: {
    pageNumber: 4,
    classification: {
      documentClass: 'holerite',
      confidence: 0.99,
      provider: 'anthropic',
      modelName: 'claude-sonnet-4-6',
    },
    validation: { status: 'validated', validatedBy: 'Dr. Souza', validatedAt: '2024-11-05T15:10:00Z' },
    ocr: {
      fullText:
        'CONTRACHEQUE — EMPRESA XYZ LTDA\nCNPJ: 12.345.678/0001-90\n\n' +
        'Funcionário: João da Silva\nCargo: Auxiliar Administrativo\nCompetência: JAN/2024\n\n' +
        'VENCIMENTOS\nSalário Base: R$ 2.500,00\nHoras Extras 50%: R$ 312,50\nTotal Bruto: R$ 2.812,50\n\n' +
        'DESCONTOS\nINSS: R$ 281,25\nIRRF: R$ 0,00\nTotal Desconto: R$ 281,25\n\nLíquido: R$ 2.531,25',
      averageConfidence: 0.97,
      hasLowConfidence: false,
      blocks: [
        { text: 'CONTRACHEQUE — EMPRESA XYZ LTDA', confidence: 0.99, lowConfidence: false },
        { text: 'Funcionário: João da Silva', confidence: 0.98, lowConfidence: false },
        { text: 'Salário Base: R$ 2.500,00', confidence: 0.97, lowConfidence: false },
        { text: 'Líquido: R$ 2.531,25', confidence: 0.96, lowConfidence: false },
      ],
    },
    inventoryItem: {
      id: 'inv-002',
      documentClass: 'holerite',
      startPage: 4,
      endPage: 7,
      pageCount: 4,
      customLabel: 'Holerites Jan–Abr 2024',
      isRelevant: true,
    },
  },
  5: {
    pageNumber: 5,
    classification: null,
    validation: { status: 'not_validated' },
    ocr: null,
    inventoryItem: null,
  },
};

/** Dado mockado padrão para páginas sem dados */
const DEFAULT_DATA = (pageNumber: number): PageSidebarData => ({
  pageNumber,
  classification: null,
  validation: { status: 'not_validated' },
  ocr: null,
  inventoryItem: null,
});

export function useSidebarData(pageNumber: number) {
  const data = useMemo<PageSidebarData>(
    () => MOCK_DATA[pageNumber] ?? DEFAULT_DATA(pageNumber),
    [pageNumber],
  );

  return { data };
}
