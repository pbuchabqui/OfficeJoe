/**
 * Componente React para visualização de páginas PDF.
 * Exibe uma página por vez com controles de navegação.
 */

import React, { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { usePDFViewer } from '../../hooks/usePDFViewer';
import { PDFViewerProps } from '../../types/pdf';
import styles from './PDFViewer.module.css';
import { ChevronLeft, ChevronRight, AlertCircle, Loader } from 'lucide-react';

export const PDFViewer: React.FC<PDFViewerProps> = ({
  url,
  width = '100%',
  height = '600px',
  onPageChange,
  className,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { state, goToPage, nextPage, previousPage, markPageLoaded } = usePDFViewer(url);
  const [inputValue, setInputValue] = useState(state.currentPage.toString());
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);

  // Carregar documento PDF
  useEffect(() => {
    const loadPDF = async () => {
      try {
        const doc = await pdfjsLib.getDocument(url).promise;
        setPdfDoc(doc);
      } catch (err) {
        console.error('Erro ao carregar PDF:', err);
      }
    };

    if (url) {
      loadPDF();
    }
  }, [url]);

  // Renderizar página no canvas
  useEffect(() => {
    const renderPage = async () => {
      if (!pdfDoc || !canvasRef.current) return;

      try {
        const page = await pdfDoc.getPage(state.currentPage);
        if (!canvasRef.current) return;

        const viewport = page.getViewport({ scale: 1.5 });

        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');

        if (!context) return;

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        await page.render({
          canvasContext: context,
          viewport,
        }).promise;

        markPageLoaded();
        setInputValue(state.currentPage.toString());

        if (onPageChange) {
          onPageChange(state.currentPage);
        }
      } catch (err) {
        console.error('Erro ao renderizar página:', err);
      }
    };

    renderPage();
  }, [state.currentPage, pdfDoc, onPageChange, markPageLoaded]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleGoToPage = () => {
    const pageNum = parseInt(inputValue, 10);
    if (!isNaN(pageNum) && pageNum > 0 && pageNum <= state.totalPages) {
      goToPage(pageNum);
    } else {
      setInputValue(state.currentPage.toString());
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleGoToPage();
    }
  };

  const containerStyle = {
    width,
    height,
  };

  return (
    <div className={`${styles.container} ${className || ''}`} style={containerStyle}>
      {/* Barra de ferramentas */}
      <div className={styles.toolbar}>
        <button
          className={styles.btn}
          onClick={previousPage}
          disabled={state.currentPage === 1 || state.loading}
          title="Página anterior"
          aria-label="Página anterior"
        >
          <ChevronLeft size={20} />
        </button>

        <div className={styles.pageInput}>
          <input
            type="number"
            min="1"
            max={state.totalPages}
            value={inputValue}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            disabled={state.loading || state.totalPages === 0}
            aria-label="Número da página"
          />
          <span className={styles.pageCount}>
            de {state.totalPages}
          </span>
        </div>

        <button
          className={styles.btn}
          onClick={handleGoToPage}
          disabled={state.loading || state.totalPages === 0}
          title="Ir para página"
          aria-label="Ir para página"
        >
          Ir
        </button>

        <button
          className={styles.btn}
          onClick={nextPage}
          disabled={state.currentPage === state.totalPages || state.loading}
          title="Próxima página"
          aria-label="Próxima página"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Área de visualização */}
      <div className={styles.viewer}>
        {state.error && (
          <div className={styles.error} role="alert">
            <AlertCircle size={24} />
            <p>{state.error}</p>
          </div>
        )}

        {state.loading && state.totalPages > 0 && (
          <div className={styles.loading}>
            <Loader size={32} className={styles.spinner} />
            <p>Carregando página...</p>
          </div>
        )}

        {!state.error && (
          <canvas
            ref={canvasRef}
            className={styles.canvas}
            style={{ display: state.loading ? 'none' : 'block' }}
          />
        )}
      </div>

      {/* Informações de página */}
      <div className={styles.info}>
        Página {state.currentPage} de {state.totalPages}
      </div>
    </div>
  );
};

export default PDFViewer;
