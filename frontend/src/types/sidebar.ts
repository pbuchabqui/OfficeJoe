/**
 * Tipos para o painel lateral do visualizador PDF.
 */

export interface ClassificationInfo {
  documentClass: string;
  confidence: number;
  provider: string;
  modelName: string;
}

export type ValidationStatusValue = 'not_validated' | 'validated' | 'rejected';

export interface ValidationInfo {
  status: ValidationStatusValue;
  validatedBy?: string;
  validatedAt?: string;
}

export interface OCRBlock {
  text: string;
  confidence: number;
  /** true quando confidence < 0.8 */
  lowConfidence: boolean;
}

export interface OCRData {
  fullText: string;
  averageConfidence: number | null;
  hasLowConfidence: boolean;
  blocks: OCRBlock[];
}

export interface InventoryItemInfo {
  id: string;
  documentClass: string;
  startPage: number;
  endPage: number;
  pageCount: number;
  customLabel: string | null;
  isRelevant: boolean;
}

export interface PageSidebarData {
  pageNumber: number;
  classification: ClassificationInfo | null;
  validation: ValidationInfo;
  ocr: OCRData | null;
  inventoryItem: InventoryItemInfo | null;
}

export interface PDFSidebarProps {
  data: PageSidebarData | null;
  /** Página atual exibida no viewer */
  currentPage: number;
  loading?: boolean;
  className?: string;
}
