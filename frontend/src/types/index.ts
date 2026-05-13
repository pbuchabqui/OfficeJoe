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

export interface DocumentProcessingProgress {
  document_id: string
  case_id: string
  status: 'processing' | 'completed' | 'failed'
  active_stage: string
  progress_percent: number
  pages_total: number
  pages_registered: number
  previews_completed: number
  ocr_completed: number
  failed_pages: number
  elapsed_seconds: number
  estimated_remaining_seconds?: number
  processing_job_id?: string
  job_status?: string
  updated_at: string
}

export interface DocumentAnalysisSummary {
  document_id: string
  case_id: string
  status: 'ready' | 'empty'
  pages_total: number
  pages_with_text: number
  text_blocks: number
  extracted_text_chars: number
  top_terms: { term: string; count: number }[]
  snippets: { page_number: number; text: string }[]
}

export interface DocumentInventoryItem {
  id: string
  document_id: string
  document_class: string
  start_page: number
  end_page: number
  page_count: number
  confidence_avg?: number
  generated_at: string
  custom_label?: string
  is_relevant: boolean
  edited_by_id?: string
  edited_at?: string
}

export interface DocumentInventory {
  document_id: string
  total_groups: number
  items: DocumentInventoryItem[]
}

export interface DocumentPericialAnalysis {
  document_id: string
  case_id: string
  status: 'completed'
  pages_total: number
  pages_classified: number
  inventory: DocumentInventory
  message: string
}

export interface OCRSearchResult {
  file_id: string
  file_page_id: string
  page_number: number
  snippet: string
  score: number
}

export interface FilePage {
  id: string
  file_id: string
  page_number: number
  width: number
  height: number
  status_ocr: string
  status_preview: string
  preview_storage_key?: string | null
  average_confidence?: number | null
  low_confidence: boolean
  created_at: string
}

export interface FilePagePreviewUrl {
  url: string
  expires_in: number
  file_page_id: string
  file_id: string
  page_number: number
}

export interface PageTextBlock {
  id: string
  file_page_id: string
  file_id: string
  page_number: number
  text: string
  x0: number
  y0: number
  x1: number
  y1: number
  confidence?: number | null
  source: string
}

export interface FilePageOCRText {
  file_page_id: string
  file_id: string
  page_number: number
  status_ocr: string
  full_text: string
  blocks: PageTextBlock[]
}

export interface PageClassification {
  id: string
  file_page_id: string
  file_id: string
  page_number: number
  document_class: string
  confidence: number
  rationale?: string | null
  provider: string
  model_name: string
  raw_response?: Record<string, unknown> | null
  human_validated: boolean
  validated_by?: string | null
  validated_at?: string | null
  created_at: string
  updated_at: string
}

export interface Extraction {
  id: string
  document_id: string
  page_number: number
  extraction_type: string
  bbox_x0?: number | null
  bbox_y0?: number | null
  bbox_x1?: number | null
  bbox_y1?: number | null
  raw_value?: string | null
  normalized_value?: string | null
  structured_data?: Record<string, unknown> | null
  confidence?: number | null
  is_reviewed: boolean
  extractor_name?: string | null
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
  tema?: string
  tipo?: string
  answers: QuesitoAnswer[]
}

export interface QuestionDraftAnswer {
  id: string
  quesito_id: string
  case_id: string
  draft_text: string
  ai_model: string
  confidence_score: number
  evidence_ids_used?: Record<string, unknown>
  generated_by_id?: string
  is_reviewed: boolean
}

export interface EvidenceItem {
  id: string
  case_id: string
  document_id: string
  page_number: number
  text_excerpt: string
  coordinates?: Record<string, unknown> | null
  evidence_type: string
  notes: string
  reliability_level: number
  validated: boolean
  validation_status: string
  validated_by?: string | null
  validated_at?: string | null
  rejection_reason?: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  total: number
  limit: number
  offset: number
  items: T[]
}

export interface EvidenceMatrixItem {
  id: string
  case_id: string
  disputed_fact: string
  theme: string
  evidence_ids: string[]
  expert_procedure: string
  methodology_or_criteria: string
  result_found: string
  technical_impact: string
  status: string
  created_at: string
  updated_at: string
}

export interface MatrixValidationResult {
  matrix_id: string
  is_valid: boolean
  summary: string
  alerts: { level: string; message: string; field?: string | null }[]
}

export interface DiligenceItem {
  id: string
  diligence_id: string
  requested_document: string
  period: string
  technical_justification: string
  status: string
  documento_recebido_id?: string | null
  status_recebimento: string
  observacao_pendencia?: string | null
  created_at: string
  updated_at: string
}

export interface Diligence {
  id: string
  case_id: string
  number: string
  recipient: string
  deadline: string
  status: string
  observations: string
  created_at: string
  updated_at: string
  items?: DiligenceItem[]
}

export interface TechnicalLimitation {
  id: string
  case_id: string
  type: string
  description: string
  technical_impact: string
  criticality: string
  status: string
  diligence_id?: string | null
  quesito_id?: string | null
  created_at: string
  updated_at: string
}

export interface Calculation {
  id: string
  case_id: string
  calculation_type: string
  description?: string | null
  responsible_user_id?: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface CalculationVersion {
  id: string
  calculation_id: string
  version_number: number
  original_filename: string
  storage_bucket: string
  storage_key: string
  sha256_hash: string
  file_size_bytes: number
  mime_type: string
  premises?: string | null
  methodology?: string | null
  created_by_id?: string | null
  created_at: string
}

export interface TechnicalDiaryEntry {
  id: string
  case_id: string
  entry_date: string
  responsible_user_id?: string | null
  decision_type: string
  description: string
  technical_justification: string
  status: string
  created_at: string
  updated_at: string
}

export interface ReportSection {
  id: string
  report_id: string
  title: string
  section_order: number
  content: string
  review_status: string
  created_at: string
  updated_at: string
}

export interface Report {
  id: string
  case_id: string
  title: string
  report_type: string
  status: string
  current_version: number
  created_at: string
  updated_at: string
  sections?: ReportSection[]
}

export interface ReportChecklistItem {
  id: string
  report_id: string
  item_key: string
  title: string
  item_order: number
  status: string
  notes?: string | null
  updated_by_id?: string | null
  created_at: string
  updated_at: string
}

export interface ReportChecklist {
  report_id: string
  total: number
  items: ReportChecklistItem[]
}

export interface ReportChecklistValidation {
  report_id: string
  can_export: boolean
  blocking_count: number
  blocking_items: { item_id: string; item_key: string; title: string; status: string; blocking: boolean }[]
  message: string
}

export interface ReportAttachment {
  id: string
  report_id: string
  attachment_type: string
  number: number
  title: string
  description?: string | null
  file_id?: string | null
  calculation_version_id?: string | null
  created_at: string
  updated_at: string
}

export interface ReportClarification {
  id: string
  case_id: string
  report_id: string
  report_version: number
  request_text: string
  theme: string
  status: string
  preliminary_response?: string | null
  final_response?: string | null
  created_at: string
  updated_at: string
}

export interface Fee {
  id: string
  case_id: string
  proposed_amount?: number | null
  arbitrated_amount?: number | null
  deposited_amount?: number | null
  withdrawn_amount?: number | null
  status: string
  proposed_at?: string | null
  arbitrated_at?: string | null
  deposited_at?: string | null
  withdrawn_at?: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface DocumentSuggestion {
  document_type: string
  description: string
  priority: string
  estimated_impact: string
}

export interface AIDocumentSuggestionResponse {
  case_id: string
  suggestions: DocumentSuggestion[]
  total_suggestions: number
}

export interface DocumentContradictionComparison {
  case_id: string
  competencia: string
  rule_key: string
  compared_count: number
  contradiction_count: number
  contradictions: {
    id: string
    competencia: string
    rubric_description: string
    delta_value?: number | null
    status: string
    created_at: string
  }[]
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
  structured_output?: Record<string, unknown>
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

export interface ChunkSearchResult {
  chunk_id: string
  document_id: string
  page_number: number
  text: string
  similarity: number
}

export interface ChunkSearchResponse {
  query: string
  total_results: number
  results: ChunkSearchResult[]
}

export interface ProcessingJob {
  id: string
  document_id: string
  case_id: string
  job_type: string
  status: string
  celery_task_id?: string | null
  error_message?: string | null
  result?: Record<string, unknown> | null
  created_at: string
  updated_at: string
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

// ── Dashboard ────────────────────────────────────────────────────────────────

export type {
  DashboardAlert,
  DashboardAlertSeverity,
  DashboardAlertTableProps,
  DashboardMetric,
  DashboardMetricKey,
  DashboardStatCardProps,
  DashboardSummary,
  DashboardTrend,
} from './dashboard'
