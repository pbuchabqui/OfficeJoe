import { apiClient } from './api'
import type { Case, Document, Quesito, SemanticSearchResult } from '@/types'

export const casesService = {
  async list(params?: { status?: string; case_type?: string }): Promise<Case[]> {
    const { data } = await apiClient.get<Case[]>('/cases', { params })
    return data
  },

  async get(id: string): Promise<Case> {
    const { data } = await apiClient.get<Case>(`/cases/${id}`)
    return data
  },

  async create(payload: Partial<Case>): Promise<Case> {
    const { data } = await apiClient.post<Case>('/cases', payload)
    return data
  },

  async update(id: string, payload: Partial<Case>): Promise<Case> {
    const { data } = await apiClient.patch<Case>(`/cases/${id}`, payload)
    return data
  },

  async listDocuments(caseId: string, params?: { status?: string; category?: string }): Promise<Document[]> {
    const { data } = await apiClient.get<Document[]>(`/cases/${caseId}/documents`, { params })
    return data
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

  async listQuesitos(caseId: string): Promise<Quesito[]> {
    const { data } = await apiClient.get<Quesito[]>(`/cases/${caseId}/quesitos`)
    return data
  },

  async createQuesito(caseId: string, payload: { sequence_number: number; origin: string; question_text: string }): Promise<Quesito> {
    const { data } = await apiClient.post<Quesito>(`/cases/${caseId}/quesitos`, payload)
    return data
  },

  async generateAIDraft(caseId: string, quesitoId: string, documentIds?: string[]) {
    const { data } = await apiClient.post(
      `/cases/${caseId}/quesitos/${quesitoId}/ai-draft`,
      { quesito_id: quesitoId, use_document_ids: documentIds ?? null }
    )
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
}
