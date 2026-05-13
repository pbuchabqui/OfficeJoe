import { apiClient } from './api'
import type {
  AIDocumentSuggestionResponse,
  AIOutput,
  Case,
  Calculation,
  CalculationVersion,
  ChunkSearchResponse,
  Diligence,
  DiligenceItem,
  Document,
  DocumentAnalysisSummary,
  DocumentContradictionComparison,
  DocumentInventory,
  DocumentInventoryItem,
  DocumentPericialAnalysis,
  DocumentProcessingProgress,
  EvidenceItem,
  EvidenceMatrixItem,
  Extraction,
  Fee,
  FilePage,
  FilePageOCRText,
  FilePagePreviewUrl,
  MatrixValidationResult,
  OCRSearchResult,
  Page,
  PageClassification,
  PaginatedResponse,
  ProcessingJob,
  QuestionDraftAnswer,
  Quesito,
  QuesitoAnswer,
  Report,
  ReportAttachment,
  ReportChecklist,
  ReportChecklistItem,
  ReportChecklistValidation,
  ReportClarification,
  ReportSection,
  SemanticSearchResult,
  TechnicalDiaryEntry,
  TechnicalLimitation,
} from '@/types'

export interface PDFIntakeResult {
  case: Case
  document_id: string
  document_filename: string
  extracted: {
    case_number?: string | null
    case_type: string
    title: string
    court?: string | null
    has_text: boolean
  }
}

export const casesService = {
  async list(params?: { status?: string; case_type?: string }): Promise<Case[]> {
    const { data } = await apiClient.get<Case[]>('/cases', { params })
    return data
  },

  async get(id: string): Promise<Case> {
    const { data } = await apiClient.get<Case>(`/cases/${id}`)
    return data
  },

  async create(payload: Record<string, unknown>): Promise<Case> {
    const { data } = await apiClient.post<Case>('/cases', payload)
    return data
  },

  async createFromPdf(file: File, category = 'autos_processuais', displayName?: string): Promise<PDFIntakeResult> {
    const form = new FormData()
    form.append('file', file)
    form.append('category', category)
    if (displayName) form.append('display_name', displayName)
    const { data } = await apiClient.post<PDFIntakeResult>(
      '/cases/from-pdf',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return data
  },

  async update(id: string, payload: Partial<Case>): Promise<Case> {
    const { data } = await apiClient.patch<Case>(`/cases/${id}`, payload)
    return data
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/cases/${id}`)
  },

  async listDocuments(caseId: string, params?: { status?: string; category?: string }): Promise<Document[]> {
    const { data } = await apiClient.get<Document[]>(`/cases/${caseId}/documents`, { params })
    return data
  },

  async getDocumentProgress(caseId: string, documentId: string): Promise<DocumentProcessingProgress> {
    const { data } = await apiClient.get<DocumentProcessingProgress>(
      `/cases/${caseId}/documents/${documentId}/processing-progress`
    )
    return data
  },

  async getDocumentAnalysisSummary(caseId: string, documentId: string): Promise<DocumentAnalysisSummary> {
    const { data } = await apiClient.get<DocumentAnalysisSummary>(
      `/cases/${caseId}/documents/${documentId}/analysis-summary`
    )
    return data
  },

  async getDocumentInventory(caseId: string, documentId: string): Promise<DocumentInventory> {
    const { data } = await apiClient.get<DocumentInventory>(
      `/cases/${caseId}/documents/${documentId}/inventory`
    )
    return data
  },

  async runPericialAnalysis(caseId: string, documentId: string): Promise<DocumentPericialAnalysis> {
    const { data } = await apiClient.post<DocumentPericialAnalysis>(
      `/cases/${caseId}/documents/${documentId}/pericial-analysis`,
      undefined,
      { timeout: 120_000 }
    )
    return data
  },

  async searchOcr(caseId: string, query: string): Promise<OCRSearchResult[]> {
    const { data } = await apiClient.get<{ results: OCRSearchResult[] }>(
      `/cases/${caseId}/ocr-search`,
      { params: { q: query, limit: 8 } }
    )
    return data.results
  },

  async uploadDocument(caseId: string, file: File, category = 'outro', displayName?: string): Promise<Document> {
    const form = new FormData()
    form.append('file', file)
    form.append('category', category)
    if (displayName) form.append('display_name', displayName)
    const { data } = await apiClient.post<Document>(
      `/cases/${caseId}/documents`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return data
  },

  async getDocumentDownloadUrl(caseId: string, documentId: string): Promise<string> {
    const { data } = await apiClient.get<{ url: string }>(
      `/cases/${caseId}/documents/${documentId}/download-url`
    )
    return data.url
  },

  async checkDocumentIntegrity(caseId: string, documentId: string) {
    const { data } = await apiClient.get(
      `/cases/${caseId}/documents/${documentId}/integrity`
    )
    return data
  },

  async listDocumentPages(caseId: string, documentId: string): Promise<Page[]> {
    const { data } = await apiClient.get<Page[]>(`/cases/${caseId}/documents/${documentId}/pages`)
    return data
  },

  async listFilePages(caseId: string, documentId: string): Promise<FilePage[]> {
    const { data } = await apiClient.get<FilePage[]>(`/cases/${caseId}/documents/${documentId}/file-pages`, {
      params: { limit: 500 },
    })
    return data
  },

  async listLowConfidenceFilePages(caseId: string, documentId: string): Promise<FilePage[]> {
    const { data } = await apiClient.get<FilePage[]>(`/cases/${caseId}/documents/${documentId}/file-pages/low-confidence`, {
      params: { limit: 500 },
    })
    return data
  },

  async getFilePagePreviewUrl(caseId: string, documentId: string, filePageId: string): Promise<FilePagePreviewUrl> {
    const { data } = await apiClient.get<FilePagePreviewUrl>(
      `/cases/${caseId}/documents/${documentId}/file-pages/${filePageId}/preview-url`
    )
    return data
  },

  async getFilePageOcrText(caseId: string, documentId: string, filePageId: string): Promise<FilePageOCRText> {
    const { data } = await apiClient.get<FilePageOCRText>(
      `/cases/${caseId}/documents/${documentId}/file-pages/${filePageId}/ocr-text`
    )
    return data
  },

  async classifyFilePage(caseId: string, documentId: string, filePageId: string): Promise<PageClassification> {
    const { data } = await apiClient.post<PageClassification>(
      `/cases/${caseId}/documents/${documentId}/file-pages/${filePageId}/classification`
    )
    return data
  },

  async getFilePageClassification(caseId: string, documentId: string, filePageId: string): Promise<PageClassification> {
    const { data } = await apiClient.get<PageClassification>(
      `/cases/${caseId}/documents/${documentId}/file-pages/${filePageId}/classification`
    )
    return data
  },

  async approveFilePageClassification(caseId: string, documentId: string, filePageId: string): Promise<PageClassification> {
    const { data } = await apiClient.post<PageClassification>(
      `/cases/${caseId}/documents/${documentId}/file-pages/${filePageId}/classification/approve`
    )
    return data
  },

  async correctFilePageClassification(caseId: string, documentId: string, filePageId: string, documentClass: string): Promise<PageClassification> {
    const { data } = await apiClient.patch<PageClassification>(
      `/cases/${caseId}/documents/${documentId}/file-pages/${filePageId}/classification`,
      { document_class: documentClass }
    )
    return data
  },

  async listDocumentExtractions(caseId: string, documentId: string): Promise<Extraction[]> {
    const { data } = await apiClient.get<Extraction[]>(`/cases/${caseId}/documents/${documentId}/extractions`)
    return data
  },

  async generateDocumentInventory(caseId: string, documentId: string): Promise<DocumentInventory> {
    const { data } = await apiClient.post<DocumentInventory>(`/cases/${caseId}/documents/${documentId}/inventory`)
    return data
  },

  async updateDocumentInventoryItem(caseId: string, documentId: string, itemId: string, payload: Partial<DocumentInventoryItem>): Promise<DocumentInventoryItem> {
    const { data } = await apiClient.patch<DocumentInventoryItem>(
      `/cases/${caseId}/documents/${documentId}/inventory/${itemId}`,
      payload
    )
    return data
  },

  async listQuesitos(caseId: string): Promise<Quesito[]> {
    const { data } = await apiClient.get<Quesito[]>(`/cases/${caseId}/quesitos`)
    return data
  },

  async createQuesito(caseId: string, payload: { sequence_number: number; origin: string; question_text: string }): Promise<Quesito> {
    const { data } = await apiClient.post<Quesito>(`/cases/${caseId}/quesitos`, payload)
    return data
  },

  async updateQuesito(caseId: string, quesitoId: string, payload: Partial<Quesito>): Promise<Quesito> {
    const { data } = await apiClient.patch<Quesito>(`/cases/${caseId}/quesitos/${quesitoId}`, payload)
    return data
  },

  async importQuesitos(caseId: string, quesitos: Array<{ sequence_number: number; origin: string; question_text: string; tema?: string; tipo?: string }>): Promise<Quesito[]> {
    const { data } = await apiClient.post<Quesito[]>(`/cases/${caseId}/quesitos/batch/import`, { quesitos })
    return data
  },

  async createQuesitoAnswer(caseId: string, quesitoId: string, payload: { answer_text: string; document_references?: unknown[] }): Promise<QuesitoAnswer> {
    const { data } = await apiClient.post<QuesitoAnswer>(`/cases/${caseId}/quesitos/${quesitoId}/answers`, payload)
    return data
  },

  async generateAIDraft(caseId: string, quesitoId: string, documentIds?: string[]) {
    const { data } = await apiClient.post(
      `/cases/${caseId}/quesitos/${quesitoId}/ai-draft`,
      { quesito_id: quesitoId, use_document_ids: documentIds ?? null }
    )
    return data
  },

  async linkQuesitoEvidence(caseId: string, quesitoId: string, evidenceItemId: string) {
    const { data } = await apiClient.post(`/cases/${caseId}/quesitos/${quesitoId}/evidence`, {
      evidence_item_id: evidenceItemId,
    })
    return data
  },

  async listQuesitoEvidence(caseId: string, quesitoId: string): Promise<EvidenceItem[]> {
    const { data } = await apiClient.get<EvidenceItem[]>(`/cases/${caseId}/quesitos/${quesitoId}/evidence`)
    return data
  },

  async generateQuestionDraft(caseId: string, quesitoId: string): Promise<QuestionDraftAnswer> {
    const { data } = await apiClient.post<QuestionDraftAnswer>(`/cases/${caseId}/quesitos/${quesitoId}/generate-draft`, {})
    return data
  },

  async semanticSearch(query: string, caseId: string, topK = 10): Promise<SemanticSearchResult[]> {
    const { data } = await apiClient.post<SemanticSearchResult[]>('/ai/search', {
      query,
      case_id: caseId,
      top_k: topK,
    })
    return data
  },

  async chunkSearch(query: string, topK = 5, minSimilarity = 0.3): Promise<ChunkSearchResponse> {
    const { data } = await apiClient.post<ChunkSearchResponse>('/search', {
      query,
      top_k: topK,
      min_similarity: minSimilarity,
    })
    return data
  },

  async getProcessingJob(jobId: string): Promise<ProcessingJob> {
    const { data } = await apiClient.get<ProcessingJob>(`/processing-jobs/${jobId}`)
    return data
  },

  async summarizeDocument(documentId: string): Promise<AIOutput> {
    const { data } = await apiClient.post<AIOutput>(`/ai/documents/${documentId}/summarize`)
    return data
  },

  async reviewAIOutput(outputId: string, payload: { review_status: string; review_note?: string }): Promise<AIOutput> {
    const { data } = await apiClient.patch<AIOutput>(`/ai/outputs/${outputId}/review`, payload)
    return data
  },

  async getDocumentSuggestions(caseId: string, context?: string): Promise<AIDocumentSuggestionResponse> {
    const { data } = await apiClient.post<AIDocumentSuggestionResponse>('/ai/document-suggestions', {
      case_id: caseId,
      context: context || null,
    })
    return data
  },

  async listEvidence(caseId: string): Promise<PaginatedResponse<EvidenceItem>> {
    const { data } = await apiClient.get<PaginatedResponse<EvidenceItem>>('/evidence', { params: { case_id: caseId } })
    return data
  },

  async createEvidence(caseId: string, payload: {
    document_id: string
    page_number: number
    text_excerpt: string
    evidence_type: string
    notes?: string
    reliability_level?: number
  }): Promise<EvidenceItem> {
    const { data } = await apiClient.post<EvidenceItem>('/evidence', {
      ...payload,
      notes: payload.notes ?? '',
      reliability_level: payload.reliability_level ?? 3,
    }, { params: { case_id: caseId } })
    return data
  },

  async validateEvidence(evidenceId: string): Promise<EvidenceItem> {
    const { data } = await apiClient.patch<EvidenceItem>(`/evidence/${evidenceId}/validate`, {})
    return data
  },

  async rejectEvidence(evidenceId: string, rejectionReason: string): Promise<EvidenceItem> {
    const { data } = await apiClient.patch<EvidenceItem>(`/evidence/${evidenceId}/reject`, {
      rejection_reason: rejectionReason,
    })
    return data
  },

  async listEvidenceMatrix(caseId: string): Promise<PaginatedResponse<EvidenceMatrixItem>> {
    const { data } = await apiClient.get<PaginatedResponse<EvidenceMatrixItem>>('/evidence-matrix', { params: { case_id: caseId } })
    return data
  },

  async createEvidenceMatrix(caseId: string, payload: Partial<EvidenceMatrixItem> & { evidence_ids: string[] }): Promise<EvidenceMatrixItem> {
    const { data } = await apiClient.post<EvidenceMatrixItem>('/evidence-matrix', payload, { params: { case_id: caseId } })
    return data
  },

  async updateEvidenceMatrix(caseId: string, matrixId: string, payload: Partial<EvidenceMatrixItem>): Promise<EvidenceMatrixItem> {
    const { data } = await apiClient.patch<EvidenceMatrixItem>(`/evidence-matrix/${matrixId}`, payload, { params: { case_id: caseId } })
    return data
  },

  async deleteEvidenceMatrix(matrixId: string): Promise<void> {
    await apiClient.delete(`/evidence-matrix/${matrixId}`)
  },

  async validateEvidenceMatrix(matrixId: string): Promise<MatrixValidationResult> {
    const { data } = await apiClient.post<MatrixValidationResult>(`/evidence-matrix/${matrixId}/validate`)
    return data
  },

  async listDiligences(caseId: string): Promise<PaginatedResponse<Diligence>> {
    const { data } = await apiClient.get<PaginatedResponse<Diligence>>('/diligences', { params: { case_id: caseId } })
    return data
  },

  async createDiligence(caseId: string, payload: {
    number: string
    recipient: string
    deadline: string
    observations?: string
    items: Array<{ requested_document: string; period: string; technical_justification: string }>
  }): Promise<Diligence> {
    const { data } = await apiClient.post<Diligence>('/diligences', {
      ...payload,
      observations: payload.observations ?? '',
    }, { params: { case_id: caseId } })
    return data
  },

  async getDiligence(diligenceId: string): Promise<Diligence> {
    const { data } = await apiClient.get<Diligence>(`/diligences/${diligenceId}`)
    return data
  },

  async updateDiligence(caseId: string, diligenceId: string, payload: Partial<Diligence>): Promise<Diligence> {
    const { data } = await apiClient.patch<Diligence>(`/diligences/${diligenceId}`, payload, { params: { case_id: caseId } })
    return data
  },

  async deleteDiligence(diligenceId: string): Promise<void> {
    await apiClient.delete(`/diligences/${diligenceId}`)
  },

  async addDiligenceItem(diligenceId: string, payload: { requested_document: string; period: string; technical_justification: string }): Promise<DiligenceItem> {
    const { data } = await apiClient.post<DiligenceItem>(`/diligences/${diligenceId}/items`, payload)
    return data
  },

  async updateDiligenceItem(diligenceId: string, itemId: string, payload: Partial<DiligenceItem>): Promise<DiligenceItem> {
    const { data } = await apiClient.patch<DiligenceItem>(`/diligences/${diligenceId}/items/${itemId}`, payload)
    return data
  },

  async registerDiligenceReceipt(diligenceId: string, itemId: string, payload: { documento_recebido_id: string; status_recebimento: string; observacao_pendencia?: string }): Promise<DiligenceItem> {
    const { data } = await apiClient.patch<DiligenceItem>(`/diligences/${diligenceId}/items/${itemId}/receipt`, payload)
    return data
  },

  async downloadDiligenceDocx(diligenceId: string): Promise<Blob> {
    const { data } = await apiClient.get<Blob>(`/diligences/${diligenceId}/download`, { responseType: 'blob' })
    return data
  },

  async listTechnicalLimitations(caseId: string): Promise<PaginatedResponse<TechnicalLimitation>> {
    const { data } = await apiClient.get<PaginatedResponse<TechnicalLimitation>>('/technical-limitations', { params: { case_id: caseId } })
    return data
  },

  async createTechnicalLimitation(caseId: string, payload: Partial<TechnicalLimitation>): Promise<TechnicalLimitation> {
    const { data } = await apiClient.post<TechnicalLimitation>('/technical-limitations', payload, { params: { case_id: caseId } })
    return data
  },

  async updateTechnicalLimitation(caseId: string, limitationId: string, payload: Partial<TechnicalLimitation>): Promise<TechnicalLimitation> {
    const { data } = await apiClient.patch<TechnicalLimitation>(`/technical-limitations/${limitationId}`, payload, { params: { case_id: caseId } })
    return data
  },

  async deleteTechnicalLimitation(limitationId: string): Promise<void> {
    await apiClient.delete(`/technical-limitations/${limitationId}`)
  },

  async createLimitationFromDiligenceItem(itemId: string): Promise<TechnicalLimitation> {
    const { data } = await apiClient.post<TechnicalLimitation>(`/technical-limitations/from-diligence/${itemId}`)
    return data
  },

  async compareDocumentContradictions(caseId: string, competencia: string): Promise<DocumentContradictionComparison> {
    const { data } = await apiClient.post<DocumentContradictionComparison>('/document-contradictions/compare', {
      case_id: caseId,
      competencia,
    })
    return data
  },

  async createCalculation(caseId: string, payload: { calculation_type: string; description?: string; status?: string }): Promise<Calculation> {
    const { data } = await apiClient.post<Calculation>(`/cases/${caseId}/calculations`, payload)
    return data
  },

  async uploadCalculationVersion(caseId: string, calculationId: string, file: File, premises?: string, methodology?: string): Promise<CalculationVersion> {
    const form = new FormData()
    form.append('file', file)
    if (premises) form.append('premises', premises)
    if (methodology) form.append('methodology', methodology)
    const { data } = await apiClient.post<CalculationVersion>(`/cases/${caseId}/calculations/${calculationId}/versions`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  async linkCalculationEvidence(caseId: string, calculationVersionId: string, evidenceItemId: string) {
    const { data } = await apiClient.post(`/cases/${caseId}/calculation-versions/${calculationVersionId}/evidence`, {
      evidence_item_id: evidenceItemId,
    })
    return data
  },

  async unlinkCalculationEvidence(caseId: string, calculationVersionId: string, evidenceItemId: string) {
    const { data } = await apiClient.delete(`/cases/${caseId}/calculation-versions/${calculationVersionId}/evidence/${evidenceItemId}`)
    return data
  },

  async listTechnicalDiary(caseId: string): Promise<PaginatedResponse<TechnicalDiaryEntry>> {
    const { data } = await apiClient.get<PaginatedResponse<TechnicalDiaryEntry>>('/technical-diary', { params: { case_id: caseId } })
    return data
  },

  async createTechnicalDiaryEntry(caseId: string, payload: { entry_date: string; decision_type: string; description: string; technical_justification: string; status?: string }): Promise<TechnicalDiaryEntry> {
    const { data } = await apiClient.post<TechnicalDiaryEntry>('/technical-diary', payload, { params: { case_id: caseId } })
    return data
  },

  async updateTechnicalDiaryEntry(caseId: string, entryId: string, payload: Partial<TechnicalDiaryEntry>): Promise<TechnicalDiaryEntry> {
    const { data } = await apiClient.patch<TechnicalDiaryEntry>(`/technical-diary/${entryId}`, payload, { params: { case_id: caseId } })
    return data
  },

  async deleteTechnicalDiaryEntry(entryId: string): Promise<void> {
    await apiClient.delete(`/technical-diary/${entryId}`)
  },

  async linkTechnicalDiaryEvidence(caseId: string, entryId: string, evidenceItemId: string) {
    const { data } = await apiClient.post(`/cases/${caseId}/technical-diary/${entryId}/evidence`, {
      evidence_item_id: evidenceItemId,
    })
    return data
  },

  async listReports(caseId: string): Promise<PaginatedResponse<Report>> {
    const { data } = await apiClient.get<PaginatedResponse<Report>>('/reports', { params: { case_id: caseId } })
    return data
  },

  async createReport(caseId: string, payload: { title: string; report_type: string; status?: string }): Promise<Report> {
    const { data } = await apiClient.post<Report>('/reports', payload, { params: { case_id: caseId } })
    return data
  },

  async getReport(reportId: string): Promise<Report> {
    const { data } = await apiClient.get<Report>(`/reports/${reportId}`)
    return data
  },

  async updateReport(caseId: string, reportId: string, payload: Partial<Report>): Promise<Report> {
    const { data } = await apiClient.patch<Report>(`/reports/${reportId}`, payload, { params: { case_id: caseId } })
    return data
  },

  async deleteReport(reportId: string): Promise<void> {
    await apiClient.delete(`/reports/${reportId}`)
  },

  async downloadReportDocx(reportId: string): Promise<Blob> {
    const { data } = await apiClient.get<Blob>(`/reports/${reportId}/download-docx`, { responseType: 'blob' })
    return data
  },

  async listReportSections(caseId: string, reportId: string): Promise<ReportSection[]> {
    const { data } = await apiClient.get<ReportSection[]>(`/reports/${reportId}/sections`, { params: { case_id: caseId } })
    return data
  },

  async createReportSection(caseId: string, reportId: string, payload: { title: string; section_order: number; content?: string; review_status?: string }): Promise<ReportSection> {
    const { data } = await apiClient.post<ReportSection>(`/reports/${reportId}/sections`, payload, { params: { case_id: caseId } })
    return data
  },

  async updateReportSection(caseId: string, sectionId: string, payload: Partial<ReportSection>): Promise<ReportSection> {
    const { data } = await apiClient.patch<ReportSection>(`/reports/sections/${sectionId}`, payload, { params: { case_id: caseId } })
    return data
  },

  async deleteReportSection(caseId: string, sectionId: string): Promise<void> {
    await apiClient.delete(`/reports/sections/${sectionId}`, { params: { case_id: caseId } })
  },

  async generateReportSectionDraft(caseId: string, sectionId: string, payload: { context?: string; instructions?: string; overwrite_existing?: boolean }) {
    const { data } = await apiClient.post(`/cases/${caseId}/report-sections/${sectionId}/draft`, payload)
    return data
  },

  async linkReportSectionMatrix(caseId: string, sectionId: string, matrixId: string) {
    const { data } = await apiClient.post(`/cases/${caseId}/report-sections/${sectionId}/evidence-matrix`, {
      evidence_matrix_item_id: matrixId,
    })
    return data
  },

  async unlinkReportSectionMatrix(caseId: string, sectionId: string, matrixId: string) {
    const { data } = await apiClient.delete(`/cases/${caseId}/report-sections/${sectionId}/evidence-matrix/${matrixId}`)
    return data
  },

  async generateReportChecklist(caseId: string, reportId: string): Promise<ReportChecklist> {
    const { data } = await apiClient.post<ReportChecklist>(`/cases/${caseId}/reports/${reportId}/checklist/generate`)
    return data
  },

  async listReportChecklist(caseId: string, reportId: string): Promise<ReportChecklist> {
    const { data } = await apiClient.get<ReportChecklist>(`/cases/${caseId}/reports/${reportId}/checklist`)
    return data
  },

  async updateReportChecklistItem(caseId: string, reportId: string, itemId: string, payload: { status: string; notes?: string }): Promise<ReportChecklistItem> {
    const { data } = await apiClient.patch<ReportChecklistItem>(`/cases/${caseId}/reports/${reportId}/checklist/items/${itemId}`, payload)
    return data
  },

  async validateReportChecklistExport(caseId: string, reportId: string): Promise<ReportChecklistValidation> {
    const { data } = await apiClient.get<ReportChecklistValidation>(`/cases/${caseId}/reports/${reportId}/checklist/export-validation`)
    return data
  },

  async listReportAttachments(caseId: string, reportId: string): Promise<ReportAttachment[]> {
    const { data } = await apiClient.get<ReportAttachment[]>(`/cases/${caseId}/reports/${reportId}/attachments`)
    return data
  },

  async createReportAttachment(caseId: string, reportId: string, payload: { attachment_type: string; title: string; description?: string; file_id?: string; calculation_version_id?: string }): Promise<ReportAttachment> {
    const { data } = await apiClient.post<ReportAttachment>(`/cases/${caseId}/reports/${reportId}/attachments`, payload)
    return data
  },

  async listReportClarifications(caseId: string): Promise<PaginatedResponse<ReportClarification>> {
    const { data } = await apiClient.get<PaginatedResponse<ReportClarification>>('/report-clarifications', { params: { case_id: caseId } })
    return data
  },

  async createReportClarification(caseId: string, payload: { report_id: string; request_text: string; theme: string; preliminary_response?: string; final_response?: string }): Promise<ReportClarification> {
    const { data } = await apiClient.post<ReportClarification>('/report-clarifications', payload, { params: { case_id: caseId } })
    return data
  },

  async updateReportClarification(caseId: string, clarificationId: string, payload: Partial<ReportClarification>): Promise<ReportClarification> {
    const { data } = await apiClient.patch<ReportClarification>(`/report-clarifications/${clarificationId}`, payload, { params: { case_id: caseId } })
    return data
  },

  async deleteReportClarification(clarificationId: string): Promise<void> {
    await apiClient.delete(`/report-clarifications/${clarificationId}`)
  },

  async listFees(caseId: string): Promise<PaginatedResponse<Fee>> {
    const { data } = await apiClient.get<PaginatedResponse<Fee>>('/fees', { params: { case_id: caseId } })
    return data
  },

  async createFee(caseId: string, payload: Partial<Fee>): Promise<Fee> {
    const { data } = await apiClient.post<Fee>('/fees', payload, { params: { case_id: caseId } })
    return data
  },

  async updateFee(caseId: string, feeId: string, payload: Partial<Fee>): Promise<Fee> {
    const { data } = await apiClient.patch<Fee>(`/fees/${feeId}`, payload, { params: { case_id: caseId } })
    return data
  },

  async deleteFee(feeId: string): Promise<void> {
    await apiClient.delete(`/fees/${feeId}`)
  },
}
