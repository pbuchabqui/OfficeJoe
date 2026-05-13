import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CaseOperationsPanel } from './CaseOperationsPanel'

const { mockCasesService } = vi.hoisted(() => ({
  mockCasesService: {
    listQuesitos: vi.fn(),
    listEvidence: vi.fn(),
    listEvidenceMatrix: vi.fn(),
    listDiligences: vi.fn(),
    listTechnicalLimitations: vi.fn(),
    listTechnicalDiary: vi.fn(),
    listReports: vi.fn(),
    listFees: vi.fn(),
    listReportClarifications: vi.fn(),
    listReportSections: vi.fn(),
    listReportChecklist: vi.fn(),
    listReportAttachments: vi.fn(),
  },
}))

vi.mock('../../services/cases', () => ({
  casesService: mockCasesService,
}))

const DOCUMENT = {
  id: 'doc-1',
  case_id: 'case-1',
  original_filename: 'autos.pdf',
  display_name: 'Autos principais',
  category: 'autos_processuais',
  sha256_hash: 'abc123abc123abc123abc123abc123',
  file_size_bytes: 1024,
  total_pages: 10,
  status: 'indexed',
  is_original_preserved: true,
  created_at: '2026-05-08T10:00:00Z',
} as const

describe('CaseOperationsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCasesService.listQuesitos.mockResolvedValue([])
    mockCasesService.listEvidence.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    mockCasesService.listEvidenceMatrix.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    mockCasesService.listDiligences.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    mockCasesService.listTechnicalLimitations.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    mockCasesService.listTechnicalDiary.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    mockCasesService.listReports.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    mockCasesService.listFees.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    mockCasesService.listReportClarifications.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    mockCasesService.listReportSections.mockResolvedValue([])
    mockCasesService.listReportChecklist.mockResolvedValue(null)
    mockCasesService.listReportAttachments.mockResolvedValue([])
  })

  it('exibe a central operacional com todos os módulos principais', async () => {
    render(<CaseOperationsPanel caseId="case-1" documents={[DOCUMENT]} />)

    expect(await screen.findByText('Fluxo pericial completo')).toBeInTheDocument()

    const tabs = screen.getByRole('tablist', { name: 'Módulos periciais' })
    expect(within(tabs).getByText('Documentos')).toBeInTheDocument()
    expect(within(tabs).getByText('Quesitos')).toBeInTheDocument()
    expect(within(tabs).getByText('Evidência e matriz')).toBeInTheDocument()
    expect(within(tabs).getByText('Diligências')).toBeInTheDocument()
    expect(within(tabs).getByText('Diário e cálculos')).toBeInTheDocument()
    expect(within(tabs).getByText('Laudos')).toBeInTheDocument()
    expect(within(tabs).getByText('IA e honorários')).toBeInTheDocument()
  })
})
