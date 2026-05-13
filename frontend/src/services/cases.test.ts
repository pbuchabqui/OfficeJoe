import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiClient } = vi.hoisted(() => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('./api', () => ({ apiClient }))

import { casesService } from './cases'

describe('casesService backend coverage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClient.get.mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } })
    apiClient.post.mockResolvedValue({ data: {} })
    apiClient.patch.mockResolvedValue({ data: {} })
    apiClient.delete.mockResolvedValue({ data: {} })
  })

  it('mapeia ferramentas documentais avançadas', async () => {
    apiClient.get.mockResolvedValueOnce({ data: [] })
    await casesService.listFilePages('case-1', 'doc-1')
    expect(apiClient.get).toHaveBeenCalledWith('/cases/case-1/documents/doc-1/file-pages', {
      params: { limit: 500 },
    })

    await casesService.classifyFilePage('case-1', 'doc-1', 'page-1')
    expect(apiClient.post).toHaveBeenCalledWith('/cases/case-1/documents/doc-1/file-pages/page-1/classification')

    await casesService.updateDocumentInventoryItem('case-1', 'doc-1', 'inv-1', { is_relevant: false })
    expect(apiClient.patch).toHaveBeenCalledWith('/cases/case-1/documents/doc-1/inventory/inv-1', {
      is_relevant: false,
    })
  })

  it('mapeia evidências, matriz, diligências e limitações', async () => {
    await casesService.createEvidence('case-1', {
      document_id: 'doc-1',
      page_number: 1,
      text_excerpt: 'Trecho',
      evidence_type: 'outro',
    })
    expect(apiClient.post).toHaveBeenCalledWith('/evidence', expect.objectContaining({
      document_id: 'doc-1',
      reliability_level: 3,
    }), { params: { case_id: 'case-1' } })

    await casesService.createEvidenceMatrix('case-1', {
      disputed_fact: 'Fato',
      theme: 'Tema',
      evidence_ids: ['ev-1'],
    })
    expect(apiClient.post).toHaveBeenCalledWith('/evidence-matrix', expect.objectContaining({
      evidence_ids: ['ev-1'],
    }), { params: { case_id: 'case-1' } })

    await casesService.createDiligence('case-1', {
      number: 'DIL-1',
      recipient: 'Parte',
      deadline: '2026-05-15T10:00:00.000Z',
      items: [{ requested_document: 'Contrato', period: '2025', technical_justification: 'Necessário' }],
    })
    expect(apiClient.post).toHaveBeenCalledWith('/diligences', expect.objectContaining({
      number: 'DIL-1',
    }), { params: { case_id: 'case-1' } })

    await casesService.createLimitationFromDiligenceItem('item-1')
    expect(apiClient.post).toHaveBeenCalledWith('/technical-limitations/from-diligence/item-1')
  })

  it('mapeia laudos, checklist, IA e honorários', async () => {
    await casesService.createReport('case-1', { title: 'Laudo', report_type: 'pericial' })
    expect(apiClient.post).toHaveBeenCalledWith('/reports', {
      title: 'Laudo',
      report_type: 'pericial',
    }, { params: { case_id: 'case-1' } })

    await casesService.generateReportChecklist('case-1', 'report-1')
    expect(apiClient.post).toHaveBeenCalledWith('/cases/case-1/reports/report-1/checklist/generate')

    await casesService.generateReportSectionDraft('case-1', 'section-1', { context: 'Contexto' })
    expect(apiClient.post).toHaveBeenCalledWith('/cases/case-1/report-sections/section-1/draft', {
      context: 'Contexto',
    })

    await casesService.getDocumentSuggestions('case-1', 'Contexto')
    expect(apiClient.post).toHaveBeenCalledWith('/ai/document-suggestions', {
      case_id: 'case-1',
      context: 'Contexto',
    })

    await casesService.chunkSearch('jornada')
    expect(apiClient.post).toHaveBeenCalledWith('/search', {
      query: 'jornada',
      top_k: 5,
      min_similarity: 0.3,
    })

    await casesService.getProcessingJob('job-1')
    expect(apiClient.get).toHaveBeenCalledWith('/processing-jobs/job-1')

    await casesService.createFee('case-1', { status: 'proposto', proposed_amount: 1000 })
    expect(apiClient.post).toHaveBeenCalledWith('/fees', {
      status: 'proposto',
      proposed_amount: 1000,
    }, { params: { case_id: 'case-1' } })
  })
})
