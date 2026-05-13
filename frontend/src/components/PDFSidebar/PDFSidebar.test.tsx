import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { PDFSidebar } from './PDFSidebar';
import { PageSidebarData } from '../../types/sidebar';

const BASE_DATA: PageSidebarData = {
  pageNumber: 1,
  classification: {
    documentClass: 'holerite',
    confidence: 0.95,
    provider: 'anthropic',
    modelName: 'claude-sonnet-4-6',
  },
  validation: { status: 'validated', validatedBy: 'Dr. Souza', validatedAt: '2024-11-05T14:30:00Z' },
  ocr: {
    fullText: 'Salário Base: R$ 2.500,00',
    averageConfidence: 0.95,
    hasLowConfidence: false,
    blocks: [{ text: 'Salário Base: R$ 2.500,00', confidence: 0.95, lowConfidence: false }],
  },
  inventoryItem: {
    id: 'inv-001',
    documentClass: 'holerite',
    startPage: 1,
    endPage: 4,
    pageCount: 4,
    customLabel: null,
    isRelevant: true,
  },
};

describe('PDFSidebar', () => {
  it('deve renderizar número da página', () => {
    render(<PDFSidebar data={BASE_DATA} currentPage={1} />);
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('deve exibir classificação documental', () => {
    render(<PDFSidebar data={BASE_DATA} currentPage={1} />);
    const classificationSection = screen.getByText('Classificação').closest('section');
    expect(classificationSection).not.toBeNull();
    expect(within(classificationSection as HTMLElement).getByText('holerite')).toBeInTheDocument();
  });

  it('deve exibir "Validado" quando status é validated', () => {
    render(<PDFSidebar data={BASE_DATA} currentPage={1} />);
    expect(screen.getByText('Validado')).toBeInTheDocument();
  });

  it('deve exibir "Não validado" quando status é not_validated', () => {
    const data: PageSidebarData = {
      ...BASE_DATA,
      validation: { status: 'not_validated' },
    };
    render(<PDFSidebar data={data} currentPage={2} />);
    expect(screen.getByText('Não validado')).toBeInTheDocument();
  });

  it('deve exibir "Rejeitado" quando status é rejected', () => {
    const data: PageSidebarData = {
      ...BASE_DATA,
      validation: { status: 'rejected' },
    };
    render(<PDFSidebar data={data} currentPage={1} />);
    expect(screen.getByText('Rejeitado')).toBeInTheDocument();
  });

  it('deve exibir texto OCR', () => {
    render(<PDFSidebar data={BASE_DATA} currentPage={1} />);
    expect(screen.getByLabelText('Texto extraído por OCR')).toBeInTheDocument();
    expect(screen.getByText(/Salário Base/)).toBeInTheDocument();
  });

  it('deve exibir alerta de baixa confiança quando hasLowConfidence=true', () => {
    const data: PageSidebarData = {
      ...BASE_DATA,
      ocr: {
        fullText: 'texto com baixa confiança',
        averageConfidence: 0.65,
        hasLowConfidence: true,
        blocks: [{ text: 'texto', confidence: 0.65, lowConfidence: true }],
      },
    };
    render(<PDFSidebar data={data} currentPage={1} />);
    expect(screen.getByText('Trechos com baixa confiança')).toBeInTheDocument();
  });

  it('não deve exibir alerta quando hasLowConfidence=false', () => {
    render(<PDFSidebar data={BASE_DATA} currentPage={1} />);
    expect(screen.queryByText('Trechos com baixa confiança')).not.toBeInTheDocument();
  });

  it('deve exibir item do inventário', () => {
    render(<PDFSidebar data={BASE_DATA} currentPage={1} />);
    expect(screen.getByText(/Págs\. 1–4/)).toBeInTheDocument();
    expect(screen.getByText(/4 páginas/)).toBeInTheDocument();
  });

  it('deve exibir customLabel do inventário quando presente', () => {
    const data: PageSidebarData = {
      ...BASE_DATA,
      inventoryItem: {
        ...BASE_DATA.inventoryItem!,
        customLabel: 'Holerites Jan–Abr',
      },
    };
    render(<PDFSidebar data={data} currentPage={1} />);
    expect(screen.getByText('Holerites Jan–Abr')).toBeInTheDocument();
  });

  it('deve exibir "Sem classificação" quando classification é null', () => {
    const data: PageSidebarData = { ...BASE_DATA, classification: null };
    render(<PDFSidebar data={data} currentPage={1} />);
    expect(screen.getByText('Sem classificação')).toBeInTheDocument();
  });

  it('deve exibir "Sem texto OCR" quando ocr é null', () => {
    const data: PageSidebarData = { ...BASE_DATA, ocr: null };
    render(<PDFSidebar data={data} currentPage={1} />);
    expect(screen.getByText('Sem texto OCR')).toBeInTheDocument();
  });

  it('deve exibir "Sem item de inventário" quando inventoryItem é null', () => {
    const data: PageSidebarData = { ...BASE_DATA, inventoryItem: null };
    render(<PDFSidebar data={data} currentPage={1} />);
    expect(screen.getByText('Sem item de inventário')).toBeInTheDocument();
  });

  it('deve exibir estado de loading', () => {
    render(<PDFSidebar data={null} currentPage={1} loading />);
    expect(screen.getByText('Carregando dados da página…')).toBeInTheDocument();
  });

  it('deve exibir nome do validador e data', () => {
    render(<PDFSidebar data={BASE_DATA} currentPage={1} />);
    expect(screen.getByText(/Dr\. Souza/)).toBeInTheDocument();
  });

  it('deve ter aria-label no painel lateral', () => {
    render(<PDFSidebar data={BASE_DATA} currentPage={1} />);
    expect(screen.getByRole('complementary', { name: 'Painel lateral da página' })).toBeInTheDocument();
  });
});
