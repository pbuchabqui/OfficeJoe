/**
 * Tipos para visualizador de PDF.
 */

export interface PDFViewerProps {
  /** URL ou base64 do PDF para exibir */
  url: string;
  /** Largura do container em pixels ou percentual */
  width?: string | number;
  /** Altura do container em pixels ou percentual */
  height?: string | number;
  /** Callback quando mudar de página */
  onPageChange?: (page: number) => void;
  /** Classe CSS customizada para o container */
  className?: string;
}

export interface PDFViewerState {
  /** Página atual (1-indexed) */
  currentPage: number;
  /** Total de páginas do documento */
  totalPages: number;
  /** Se está carregando o PDF ou página atual */
  loading: boolean;
  /** Mensagem de erro, se houver */
  error: string | null;
}

export interface PDFDocument {
  numPages: number;
  getPage: (pageNumber: number) => Promise<PDFPage>;
}

export interface PDFPage {
  getViewport: (options: { scale: number }) => {
    width: number;
    height: number;
  };
  render: (options: PDFRenderOptions) => { promise: Promise<void> };
}

export interface PDFRenderOptions {
  canvasContext: CanvasRenderingContext2D;
  viewport: {
    width: number;
    height: number;
  };
}
