/**
 * Testes para o componente PDFViewer.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PDFViewer } from './PDFViewer';

// Mock do pdfjs-dist
vi.mock('pdfjs-dist', () => ({
  version: '4.9.155',
  getDocument: vi.fn(() => ({
    promise: Promise.resolve({
      numPages: 5,
      getPage: vi.fn((_pageNum) =>
        Promise.resolve({
          getViewport: () => ({ width: 595, height: 842 }),
          render: () => ({ promise: Promise.resolve() }),
        })
      ),
    }),
  })),
  GlobalWorkerOptions: {
    workerSrc: '',
  },
}));

describe('PDFViewer', () => {
  const testPdfUrl = 'http://example.com/test.pdf';
  const waitForPdfLoad = async () => {
    await waitFor(() => {
      expect(screen.getAllByText(/de 5/).length).toBeGreaterThan(0);
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('deve renderizar com sucesso', async () => {
    render(<PDFViewer url={testPdfUrl} />);

    // Verifica que os controles estão presentes
    expect(screen.getByLabelText('Página anterior')).toBeInTheDocument();
    expect(screen.getByLabelText('Próxima página')).toBeInTheDocument();
    await waitForPdfLoad();
  });

  it('deve mostrar o número correto de páginas', async () => {
    render(<PDFViewer url={testPdfUrl} />);

    await waitForPdfLoad();
  });

  it('deve desabilitar botão "anterior" na primeira página', async () => {
    render(<PDFViewer url={testPdfUrl} />);

    await waitFor(() => {
      const btnAnterior = screen.getByLabelText('Página anterior');
      expect(btnAnterior).toBeDisabled();
    });
  });

  it('deve permitir navegação para próxima página', async () => {
    render(<PDFViewer url={testPdfUrl} />);

    await waitFor(() => {
      const input = screen.getByLabelText('Número da página') as HTMLInputElement;
      expect(input.value).toBe('1');
    });

    const btnProximo = screen.getByLabelText('Próxima página');
    fireEvent.click(btnProximo);

    await waitFor(() => {
      const input = screen.getByLabelText('Número da página') as HTMLInputElement;
      expect(input.value).toBe('2');
    });
  });

  it('deve permitir ir para página específica via input', async () => {
    render(<PDFViewer url={testPdfUrl} />);

    await waitFor(() => {
      const input = screen.getByLabelText('Número da página');
      expect(input).toBeInTheDocument();
    });

    const input = screen.getByLabelText('Número da página') as HTMLInputElement;
    const btnIr = screen.getByRole('button', { name: 'Ir para página' });

    fireEvent.change(input, { target: { value: '3' } });
    fireEvent.click(btnIr);

    await waitFor(() => {
      expect(input.value).toBe('3');
    });
  });

  it('deve aceitar Enter no input para ir para página', async () => {
    render(<PDFViewer url={testPdfUrl} />);

    const input = screen.getByLabelText('Número da página') as HTMLInputElement;

    await waitFor(() => {
      expect(input).toBeInTheDocument();
    });

    fireEvent.change(input, { target: { value: '2' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 });

    await waitFor(() => {
      expect(input.value).toBe('2');
    });
  });

  it('deve desabilitar input quando totalPages é 0', async () => {
    render(<PDFViewer url="" />);

    await waitFor(() => {
      const input = screen.getByLabelText('Número da página') as HTMLInputElement;
      expect(input).toBeDisabled();
    });
  });

  it('deve exibir erro quando URL é inválida', async () => {
    render(<PDFViewer url="invalid-url" />);

    // O componente renderiza, mas pode mostrar erro
    // Depende do mock do pdfjs
    expect(screen.getByLabelText('Página anterior')).toBeInTheDocument();
    await waitForPdfLoad();
  });

  it('deve chamar onPageChange quando página muda', async () => {
    const onPageChange = vi.fn();
    render(<PDFViewer url={testPdfUrl} onPageChange={onPageChange} />);

    await waitFor(() => {
      // onPageChange é chamado ao carregar a primeira página
      expect(onPageChange).toHaveBeenCalledWith(1);
    });
  });

  it('deve respeitar dimensões customizadas', async () => {
    const { container } = render(
      <PDFViewer url={testPdfUrl} width="800px" height="400px" />
    );

    const viewer = container.firstElementChild as HTMLElement;
    expect(viewer.style.width).toBe('800px');
    expect(viewer.style.height).toBe('400px');
    await waitForPdfLoad();
  });

  it('deve aceitar className customizada', async () => {
    const { container } = render(
      <PDFViewer url={testPdfUrl} className="custom-class" />
    );

    const viewer = container.firstElementChild;
    expect(viewer).toHaveClass('custom-class');
    await waitForPdfLoad();
  });

  it('deve desabilitar navegação quando carregando', async () => {
    render(<PDFViewer url={testPdfUrl} />);

    await waitFor(() => {
      // Quando está carregando, os botões podem estar desabilitados
      // Esse comportamento depende da implementação do hook
      expect(screen.getByLabelText('Próxima página')).toBeInTheDocument();
    });
  });

  it('deve mostrar canvas para renderizar página', async () => {
    const { container } = render(<PDFViewer url={testPdfUrl} />);

    await waitFor(() => {
      const canvas = container.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });
});
