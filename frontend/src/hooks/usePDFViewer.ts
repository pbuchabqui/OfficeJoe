/**
 * Hook para gerenciar estado do visualizador de PDF.
 * Cuida de: carregamento, navegação entre páginas, erro.
 */

import { useState, useEffect, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { PDFViewerState } from '../types/pdf';

// Configure o worker para pdfjs-dist
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

export function usePDFViewer(url: string) {
  const [state, setState] = useState<PDFViewerState>({
    currentPage: 1,
    totalPages: 0,
    loading: true,
    error: null,
  });

  // Carregar o PDF e obter número de páginas
  useEffect(() => {
    if (!url) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: 'URL do PDF não fornecida',
      }));
      return;
    }

    let isMounted = true;

    const loadPDF = async () => {
      try {
        setState((prev) => ({
          ...prev,
          loading: true,
          error: null,
        }));

        const pdf = await pdfjsLib.getDocument(url).promise;

        if (isMounted) {
          setState((prev) => ({
            ...prev,
            totalPages: pdf.numPages,
            currentPage: 1,
            loading: false,
          }));
        }
      } catch (err) {
        if (isMounted) {
          setState((prev) => ({
            ...prev,
            error: `Erro ao carregar PDF: ${err instanceof Error ? err.message : 'Desconhecido'}`,
            loading: false,
          }));
        }
      }
    };

    loadPDF();

    return () => {
      isMounted = false;
    };
  }, [url]);

  const goToPage = useCallback((pageNumber: number) => {
    setState((prev) => ({
      ...prev,
      currentPage: Math.max(1, Math.min(pageNumber, prev.totalPages)),
      loading: true,
    }));
  }, []);

  const nextPage = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentPage: Math.min(prev.currentPage + 1, prev.totalPages),
      loading: true,
    }));
  }, []);

  const previousPage = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentPage: Math.max(prev.currentPage - 1, 1),
      loading: true,
    }));
  }, []);

  const markPageLoaded = useCallback(() => {
    setState((prev) => ({
      ...prev,
      loading: false,
    }));
  }, []);

  return {
    state,
    goToPage,
    nextPage,
    previousPage,
    markPageLoaded,
  };
}
