// ── Autenticação ─────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'perito' | 'assistente' | 'visualizador'
  is_active: boolean
  otp_enabled: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// ── Processos ─────────────────────────────────────────────────────────────────

export type CaseStatus =
  | 'planejamento'
  | 'diligencias'
  | 'analise'
  | 'calculos'
  | 'laudo_rascunho'
  | 'laudo_revisao'
  | 'laudo_protocolado'
  | 'esclarecimentos'
  | 'encerrado'
  | 'suspenso'

export type CaseType = 'trabalhista' | 'civel' | 'fiscal' | 'extrajudicial' | 'arbitragem'

export interface CaseParty {
  id: string
  case_id: string
  name: string
  role: string
  cpf_cnpj?: string
  lawyer_name?: string
  lawyer_oab?: string
}

export interface Case {
  id: string
  case_number: string
  case_type: CaseType
  status: CaseStatus
  title: string
  description?: string
  court?: string
  court_district?: string
  judge_name?: string
  appointment_date?: string
  deadline_date?: string
  filing_date?: string
  honorarium_proposed?: number
  honorarium_approved?: number
  responsible_user_id?: string
  parties: CaseParty[]
}

// ── Documentos ────────────────────────────────────────────────────────────────

export type DocumentStatus =
  | 'uploaded'
  | 'hashing'
  | 'queued_ocr'
  | 'ocr_running'
  | 'ocr_completed'
  | 'ocr_failed'
  | 'extracting'
  | 'indexed'
  | 'error'
  | 'archived'

export interface Document {
  id: string
  case_id: string
  original_filename: string
  display_name?: string
  category: string
  sha256_hash: string
  file_size_bytes: number
  total_pages?: number
  status: DocumentStatus
  ocr_engine_used?: string
  ocr_avg_confidence?: string
  error_message?: string
  is_original_preserved: boolean
  created_at: string
}

export interface Page {
  id: string
  document_id: string
  page_number: number
  raw_text?: string
  ocr_engine?: string
  ocr_confidence?: number
  has_text_layer: boolean
  is_image_only: boolean
  width_pt?: number
  height_pt?: number
  text_blocks?: TextBlock[]
  tables_detected?: TableData[]
}

export interface TextBlock {
  text: string
  x0: number
  y0: number
  x1: number
  y1: number
  confidence: number
  source: string
}

export interface TableData {
  rows: string[][]
  page: number
}

// ── Quesitos ──────────────────────────────────────────────────────────────────

export type QuesitoStatus = 'pendente' | 'em_analise' | 'respondido' | 'revisado' | 'aprovado'

export interface QuesitoAnswer {
  id: string
  quesito_id: string
  version: number
  answer_text: string
  document_references?: DocumentReference[]
  generated_by_ai: boolean
  ai_model?: string
  ai_confidence?: number
  is_human_reviewed: boolean
  review_note?: string
}

export interface DocumentReference {
  document_id: string
  document_name?: string
  page_number: number
  excerpt?: string
}

export interface Quesito {
  id: string
  case_id: string
  sequence_number: number
  origin: string
  status: QuesitoStatus
  question_text: string
  answers: QuesitoAnswer[]
}

// ── IA ────────────────────────────────────────────────────────────────────────

export interface AISource {
  document_id?: string
  document_name?: string
  page_number?: number
  excerpt?: string
  confidence?: number
}

export interface AIOutput {
  id: string
  output_type: string
  ai_provider: string
  ai_model: string
  output_text?: string
  sources?: AISource[]
  overall_confidence?: number
  review_status: 'pending_review' | 'approved' | 'rejected' | 'partially_approved'
  has_documental_basis: boolean
  prompt_tokens?: number
  completion_tokens?: number
}

export interface SemanticSearchResult {
  chunk_text: string
  page_number: number
  document_id: string
  document_name?: string
  similarity: number
  page_id: string
}

// ── API Errors ─────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}

// ── PDF Viewer ────────────────────────────────────────────────────────────────

export type { PDFViewerProps, PDFViewerState, PDFDocument, PDFPage, PDFRenderOptions } from './pdf'

// ── PDF Sidebar ───────────────────────────────────────────────────────────────

export type {
  ClassificationInfo,
  ValidationStatusValue,
  ValidationInfo,
  OCRBlock,
  OCRData,
  InventoryItemInfo,
  PageSidebarData,
  PDFSidebarProps,
} from './sidebar'
