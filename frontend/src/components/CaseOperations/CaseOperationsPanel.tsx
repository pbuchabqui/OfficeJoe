import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Bot,
  Calculator,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileText,
  Gavel,
  Loader2,
  NotebookPen,
  ReceiptText,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
import { extractErrorMessage } from '../../services/api'
import { authService } from '../../services/auth'
import { casesService } from '../../services/cases'
import type {
  AIDocumentSuggestionResponse,
  AIOutput,
  Calculation,
  CalculationVersion,
  ChunkSearchResponse,
  Diligence,
  Document,
  DocumentContradictionComparison,
  DocumentInventory,
  EvidenceItem,
  EvidenceMatrixItem,
  Fee,
  FilePage,
  FilePageOCRText,
  MatrixValidationResult,
  ProcessingJob,
  QuestionDraftAnswer,
  Quesito,
  Report,
  ReportAttachment,
  ReportChecklist,
  ReportChecklistValidation,
  ReportClarification,
  ReportSection,
  SemanticSearchResult,
  TechnicalDiaryEntry,
  TechnicalLimitation,
} from '../../types'
import styles from './CaseOperationsPanel.module.css'

type Notice = { tone: 'success' | 'error'; text: string } | null
type OperationsTab = 'documents' | 'quesitos' | 'evidence' | 'diligences' | 'diary' | 'reports' | 'finance-ai'

const EVIDENCE_TYPES = [
  'contrato',
  'depoimento',
  'documento_financeiro',
  'holerite',
  'nota_fiscal',
  'extrato_bancario',
  'email',
  'mensagem',
  'foto',
  'audio',
  'outro',
]

const DOCUMENT_CLASSES = [
  'holerite',
  'ficha financeira',
  'cartão ponto',
  'sentença',
  'acórdão',
  'decisão',
  'petição inicial',
  'contestação',
  'laudo',
  'parecer',
  'contrato',
  'extrato',
  'nota fiscal',
  'CCT',
  'ACT',
  'TRCT',
  'e-mail',
  'planilha',
  'documento ilegível',
  'outro',
]

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

function nextWeekLocal() {
  const date = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
  return date.toISOString().slice(0, 16)
}

function asDateTime(value: string) {
  return value ? new Date(value).toISOString() : new Date().toISOString()
}

function money(value?: number | null) {
  if (value === undefined || value === null) return '-'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function shortId(value?: string | null) {
  return value ? value.slice(0, 8) : '-'
}

export function CaseOperationsPanel({
  caseId,
  documents,
}: {
  caseId: string
  documents: Document[]
}) {
  const [activeTab, setActiveTab] = useState<OperationsTab>('documents')
  const [notice, setNotice] = useState<Notice>(null)
  const [loading, setLoading] = useState(false)
  const [busyAction, setBusyAction] = useState<string | null>(null)

  const [quesitos, setQuesitos] = useState<Quesito[]>([])
  const [evidence, setEvidence] = useState<EvidenceItem[]>([])
  const [matrix, setMatrix] = useState<EvidenceMatrixItem[]>([])
  const [diligences, setDiligences] = useState<Diligence[]>([])
  const [limitations, setLimitations] = useState<TechnicalLimitation[]>([])
  const [diary, setDiary] = useState<TechnicalDiaryEntry[]>([])
  const [reports, setReports] = useState<Report[]>([])
  const [fees, setFees] = useState<Fee[]>([])
  const [clarifications, setClarifications] = useState<ReportClarification[]>([])

  const [selectedDocumentId, setSelectedDocumentId] = useState(documents[0]?.id ?? '')
  const [filePages, setFilePages] = useState<FilePage[]>([])
  const [selectedFilePageId, setSelectedFilePageId] = useState('')
  const [documentInventory, setDocumentInventory] = useState<DocumentInventory | null>(null)
  const [documentToolResult, setDocumentToolResult] = useState<unknown>(null)
  const [ocrText, setOcrText] = useState<FilePageOCRText | null>(null)
  const [correctClass, setCorrectClass] = useState('outro')
  const [processingJobId, setProcessingJobId] = useState('')
  const [processingJob, setProcessingJob] = useState<ProcessingJob | null>(null)

  const [selectedQuesitoId, setSelectedQuesitoId] = useState('')
  const [questionDraft, setQuestionDraft] = useState<QuestionDraftAnswer | null>(null)
  const [qEvidence, setQEvidence] = useState<EvidenceItem[]>([])
  const [quesitoForm, setQuesitoForm] = useState({ sequence: '1', origin: 'juizo', text: '', tema: '', tipo: '' })
  const [batchQuesitos, setBatchQuesitos] = useState('')
  const [answerText, setAnswerText] = useState('')

  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>([])
  const [evidenceForm, setEvidenceForm] = useState({
    documentId: documents[0]?.id ?? '',
    page: '1',
    type: 'outro',
    reliability: '3',
    text: '',
    notes: '',
  })
  const [matrixForm, setMatrixForm] = useState({
    disputed_fact: '',
    theme: '',
    expert_procedure: '',
    methodology_or_criteria: '',
    result_found: '',
    technical_impact: '',
  })
  const [matrixValidation, setMatrixValidation] = useState<MatrixValidationResult | null>(null)

  const [diligenceForm, setDiligenceForm] = useState({
    number: 'DIL-001',
    recipient: '',
    deadline: nextWeekLocal(),
    observations: '',
    requested_document: '',
    period: '',
    technical_justification: '',
  })
  const [selectedDiligence, setSelectedDiligence] = useState<Diligence | null>(null)
  const [receiptForm, setReceiptForm] = useState({ itemId: '', documentId: documents[0]?.id ?? '', status: 'recebido', note: '' })
  const [limitationForm, setLimitationForm] = useState({
    type: '',
    description: '',
    technical_impact: '',
    criticality: 'média',
  })

  const [calculationForm, setCalculationForm] = useState({ calculation_type: 'horas_extras', description: '', status: 'rascunho' })
  const [createdCalculations, setCreatedCalculations] = useState<Calculation[]>([])
  const [selectedCalculationId, setSelectedCalculationId] = useState('')
  const [calculationFile, setCalculationFile] = useState<File | null>(null)
  const [calculationVersionForm, setCalculationVersionForm] = useState({ premises: '', methodology: '' })
  const [calculationVersions, setCalculationVersions] = useState<CalculationVersion[]>([])
  const [diaryForm, setDiaryForm] = useState({
    entry_date: todayISO(),
    decision_type: '',
    description: '',
    technical_justification: '',
    status: 'draft',
  })

  const [reportForm, setReportForm] = useState({ title: '', report_type: 'laudo_pericial', status: 'rascunho' })
  const [selectedReportId, setSelectedReportId] = useState('')
  const [reportSections, setReportSections] = useState<ReportSection[]>([])
  const [reportChecklist, setReportChecklist] = useState<ReportChecklist | null>(null)
  const [reportChecklistValidation, setReportChecklistValidation] = useState<ReportChecklistValidation | null>(null)
  const [reportAttachments, setReportAttachments] = useState<ReportAttachment[]>([])
  const [sectionForm, setSectionForm] = useState({ title: '', section_order: '1', content: '', review_status: 'pendente' })
  const [draftForm, setDraftForm] = useState({ sectionId: '', context: '', instructions: '', overwrite: false })
  const [attachmentForm, setAttachmentForm] = useState({ type: 'anexo', title: '', description: '', fileId: '', calculationVersionId: '' })
  const [clarificationForm, setClarificationForm] = useState({ reportId: '', theme: '', request_text: '', preliminary_response: '', final_response: '' })

  const [feeForm, setFeeForm] = useState({ proposed_amount: '', arbitrated_amount: '', deposited_amount: '', withdrawn_amount: '', status: 'proposto', notes: '' })
  const [semanticQuery, setSemanticQuery] = useState('')
  const [semanticResults, setSemanticResults] = useState<SemanticSearchResult[]>([])
  const [chunkSearchResults, setChunkSearchResults] = useState<ChunkSearchResponse | null>(null)
  const [suggestionContext, setSuggestionContext] = useState('')
  const [suggestions, setSuggestions] = useState<AIDocumentSuggestionResponse | null>(null)
  const [aiOutput, setAiOutput] = useState<AIOutput | null>(null)
  const [contradictionMonth, setContradictionMonth] = useState('')
  const [contradictions, setContradictions] = useState<DocumentContradictionComparison | null>(null)
  const [userForm, setUserForm] = useState({ email: '', password: '', full_name: '', role: 'assistente' })

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId) ?? documents[0],
    [documents, selectedDocumentId]
  )

  const selectedReport = useMemo(
    () => reports.find((report) => report.id === selectedReportId),
    [reports, selectedReportId]
  )

  const firstEvidenceId = evidence[0]?.id ?? ''

  const loadReportWorkspace = useCallback(async (reportId: string) => {
    if (!reportId) {
      setReportSections([])
      setReportChecklist(null)
      setReportAttachments([])
      return
    }
    const [sections, checklist, attachments] = await Promise.all([
      casesService.listReportSections(caseId, reportId).catch(() => []),
      casesService.listReportChecklist(caseId, reportId).catch(() => null),
      casesService.listReportAttachments(caseId, reportId).catch(() => []),
    ])
    setReportSections(sections)
    setReportChecklist(checklist)
    setReportAttachments(attachments)
    setDraftForm((prev) => ({ ...prev, sectionId: prev.sectionId || sections[0]?.id || '' }))
  }, [caseId])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [
        qResult,
        evidenceResult,
        matrixResult,
        diligenceResult,
        limitationResult,
        diaryResult,
        reportResult,
        feeResult,
        clarificationResult,
      ] = await Promise.all([
        casesService.listQuesitos(caseId).catch(() => []),
        casesService.listEvidence(caseId).then((response) => response.items).catch(() => []),
        casesService.listEvidenceMatrix(caseId).then((response) => response.items).catch(() => []),
        casesService.listDiligences(caseId).then((response) => response.items).catch(() => []),
        casesService.listTechnicalLimitations(caseId).then((response) => response.items).catch(() => []),
        casesService.listTechnicalDiary(caseId).then((response) => response.items).catch(() => []),
        casesService.listReports(caseId).then((response) => response.items).catch(() => []),
        casesService.listFees(caseId).then((response) => response.items).catch(() => []),
        casesService.listReportClarifications(caseId).then((response) => response.items).catch(() => []),
      ])
      setQuesitos(qResult)
      setEvidence(evidenceResult)
      setMatrix(matrixResult)
      setDiligences(diligenceResult)
      setLimitations(limitationResult)
      setDiary(diaryResult)
      setReports(reportResult)
      setFees(feeResult)
      setClarifications(clarificationResult)

      if (!selectedQuesitoId && qResult[0]) setSelectedQuesitoId(qResult[0].id)
      if (selectedEvidenceIds.length === 0 && evidenceResult[0]) setSelectedEvidenceIds([evidenceResult[0].id])
      const nextReportId = selectedReportId || reportResult[0]?.id || ''
      if (!selectedReportId && nextReportId) setSelectedReportId(nextReportId)
      await loadReportWorkspace(nextReportId)
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setLoading(false)
    }
  }, [caseId, loadReportWorkspace, selectedEvidenceIds.length, selectedQuesitoId, selectedReportId])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  useEffect(() => {
    if (!selectedDocumentId && documents[0]) {
      setSelectedDocumentId(documents[0].id)
      setEvidenceForm((prev) => ({ ...prev, documentId: documents[0].id }))
      setReceiptForm((prev) => ({ ...prev, documentId: documents[0].id }))
    }
  }, [documents, selectedDocumentId])

  useEffect(() => {
    loadReportWorkspace(selectedReportId)
  }, [selectedReportId, loadReportWorkspace])

  async function runAction<T>(label: string, action: () => Promise<T>, reload = true): Promise<T | null> {
    setBusyAction(label)
    setNotice(null)
    try {
      const result = await action()
      setNotice({ tone: 'success', text: `${label} concluído.` })
      if (reload) await loadAll()
      return result
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
      return null
    } finally {
      setBusyAction(null)
    }
  }

  async function handleLoadDocumentTools() {
    if (!selectedDocument) return
    const result = await runAction('Consulta documental', async () => {
      const [pages, filePageList, lowConfidence, extractions, inventory] = await Promise.all([
        casesService.listDocumentPages(caseId, selectedDocument.id),
        casesService.listFilePages(caseId, selectedDocument.id),
        casesService.listLowConfidenceFilePages(caseId, selectedDocument.id),
        casesService.listDocumentExtractions(caseId, selectedDocument.id),
        casesService.getDocumentInventory(caseId, selectedDocument.id),
      ])
      return { pages, filePageList, lowConfidence, extractions, inventory }
    }, false)
    if (!result) return
    setFilePages(result.filePageList)
    setSelectedFilePageId(result.filePageList[0]?.id ?? '')
    setDocumentInventory(result.inventory)
    setDocumentToolResult({
      pages: result.pages.length,
      file_pages: result.filePageList.length,
      low_confidence_pages: result.lowConfidence.length,
      extractions: result.extractions.length,
      inventory_groups: result.inventory.total_groups,
    })
  }

  async function handleDownloadDocument() {
    if (!selectedDocument) return
    const url = await runAction('URL de download', () => casesService.getDocumentDownloadUrl(caseId, selectedDocument.id), false)
    if (url) window.open(url, '_blank', 'noopener,noreferrer')
  }

  async function handleFilePageAction(action: 'ocr' | 'classify' | 'approve' | 'correct' | 'preview') {
    if (!selectedDocument || !selectedFilePageId) return
    if (action === 'ocr') {
      const result = await runAction('OCR da página', () => casesService.getFilePageOcrText(caseId, selectedDocument.id, selectedFilePageId), false)
      if (result) setOcrText(result)
      return
    }
    if (action === 'preview') {
      const result = await runAction('Preview da página', () => casesService.getFilePagePreviewUrl(caseId, selectedDocument.id, selectedFilePageId), false)
      if (result) window.open(result.url, '_blank', 'noopener,noreferrer')
      return
    }
    if (action === 'classify') {
      const result = await runAction('Classificação da página', () => casesService.classifyFilePage(caseId, selectedDocument.id, selectedFilePageId), false)
      if (result) setDocumentToolResult(result)
      return
    }
    if (action === 'approve') {
      const result = await runAction('Aprovação da classificação', () => casesService.approveFilePageClassification(caseId, selectedDocument.id, selectedFilePageId), false)
      if (result) setDocumentToolResult(result)
      return
    }
    const result = await runAction('Correção da classificação', () => casesService.correctFilePageClassification(caseId, selectedDocument.id, selectedFilePageId, correctClass), false)
    if (result) setDocumentToolResult(result)
  }

  async function handleCreateQuesito(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const created = await runAction('Quesito', () => casesService.createQuesito(caseId, {
      sequence_number: Number(quesitoForm.sequence),
      origin: quesitoForm.origin,
      question_text: quesitoForm.text,
      tema: quesitoForm.tema || undefined,
      tipo: quesitoForm.tipo || undefined,
    } as Parameters<typeof casesService.createQuesito>[1]))
    if (created) {
      setSelectedQuesitoId(created.id)
      setQuesitoForm((prev) => ({ ...prev, sequence: String(Number(prev.sequence) + 1), text: '', tema: '', tipo: '' }))
    }
  }

  async function handleImportQuesitos(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const items = batchQuesitos
      .split('\n')
      .map((line, index) => line.trim() ? ({
        sequence_number: index + 1,
        origin: 'juizo',
        question_text: line.trim(),
      }) : null)
      .filter(Boolean) as Array<{ sequence_number: number; origin: string; question_text: string }>
    if (items.length === 0) return
    const result = await runAction('Importação de quesitos', () => casesService.importQuesitos(caseId, items))
    if (result) setBatchQuesitos('')
  }

  async function handleQuesitoAI(kind: 'answer' | 'draft' | 'evidence') {
    if (!selectedQuesitoId) return
    if (kind === 'answer') {
      await runAction('Resposta IA do quesito', () => casesService.generateAIDraft(caseId, selectedQuesitoId))
    } else if (kind === 'draft') {
      const result = await runAction('Minuta com evidências', () => casesService.generateQuestionDraft(caseId, selectedQuesitoId), false)
      if (result) setQuestionDraft(result)
    } else {
      const result = await runAction('Evidências do quesito', () => casesService.listQuesitoEvidence(caseId, selectedQuesitoId), false)
      if (result) setQEvidence(result)
    }
  }

  async function handleCreateAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedQuesitoId || !answerText.trim()) return
    const result = await runAction('Resposta manual', () => casesService.createQuesitoAnswer(caseId, selectedQuesitoId, {
      answer_text: answerText.trim(),
    }))
    if (result) setAnswerText('')
  }

  async function handleCreateEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = await runAction('Evidência', () => casesService.createEvidence(caseId, {
      document_id: evidenceForm.documentId,
      page_number: Number(evidenceForm.page),
      text_excerpt: evidenceForm.text,
      evidence_type: evidenceForm.type,
      reliability_level: Number(evidenceForm.reliability),
      notes: evidenceForm.notes,
    }))
    if (result) {
      setEvidenceForm((prev) => ({ ...prev, text: '', notes: '' }))
      setSelectedEvidenceIds([result.id])
    }
  }

  async function handleCreateMatrix(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (selectedEvidenceIds.length === 0) return
    const result = await runAction('Item da matriz', () => casesService.createEvidenceMatrix(caseId, {
      ...matrixForm,
      evidence_ids: selectedEvidenceIds,
    }))
    if (result) setMatrixForm({ disputed_fact: '', theme: '', expert_procedure: '', methodology_or_criteria: '', result_found: '', technical_impact: '' })
  }

  async function handleCreateDiligence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = await runAction('Diligência', () => casesService.createDiligence(caseId, {
      number: diligenceForm.number,
      recipient: diligenceForm.recipient,
      deadline: asDateTime(diligenceForm.deadline),
      observations: diligenceForm.observations,
      items: [{
        requested_document: diligenceForm.requested_document,
        period: diligenceForm.period,
        technical_justification: diligenceForm.technical_justification,
      }],
    }))
    if (result) setDiligenceForm((prev) => ({ ...prev, requested_document: '', period: '', technical_justification: '' }))
  }

  async function handleSelectDiligence(diligenceId: string) {
    const result = await runAction('Detalhe da diligência', () => casesService.getDiligence(diligenceId), false)
    if (result) {
      setSelectedDiligence(result)
      setReceiptForm((prev) => ({ ...prev, itemId: result.items?.[0]?.id ?? '' }))
    }
  }

  async function handleCreateLimitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = await runAction('Limitação técnica', () => casesService.createTechnicalLimitation(caseId, limitationForm))
    if (result) setLimitationForm({ type: '', description: '', technical_impact: '', criticality: 'média' })
  }

  async function handleCreateCalculation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = await runAction('Controle de cálculo', () => casesService.createCalculation(caseId, calculationForm), false)
    if (result) {
      setCreatedCalculations((prev) => [result, ...prev])
      setSelectedCalculationId(result.id)
      setCalculationForm({ calculation_type: 'horas_extras', description: '', status: 'rascunho' })
    }
  }

  async function handleUploadCalculationVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedCalculationId || !calculationFile) return
    const result = await runAction('Versão de cálculo', () => casesService.uploadCalculationVersion(
      caseId,
      selectedCalculationId,
      calculationFile,
      calculationVersionForm.premises,
      calculationVersionForm.methodology
    ), false)
    if (result) {
      setCalculationVersions((prev) => [result, ...prev])
      setCalculationFile(null)
      setCalculationVersionForm({ premises: '', methodology: '' })
    }
  }

  async function handleCreateDiary(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = await runAction('Entrada do diário', () => casesService.createTechnicalDiaryEntry(caseId, diaryForm))
    if (result) setDiaryForm({ entry_date: todayISO(), decision_type: '', description: '', technical_justification: '', status: 'draft' })
  }

  async function handleCreateReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = await runAction('Laudo', () => casesService.createReport(caseId, reportForm))
    if (result) {
      setSelectedReportId(result.id)
      setClarificationForm((prev) => ({ ...prev, reportId: result.id }))
      setReportForm({ title: '', report_type: 'laudo_pericial', status: 'rascunho' })
    }
  }

  async function handleCreateSection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedReportId) return
    const result = await runAction('Seção do laudo', () => casesService.createReportSection(caseId, selectedReportId, {
      title: sectionForm.title,
      section_order: Number(sectionForm.section_order),
      content: sectionForm.content,
      review_status: sectionForm.review_status,
    }))
    if (result) setSectionForm((prev) => ({ ...prev, title: '', content: '', section_order: String(Number(prev.section_order) + 1) }))
  }

  async function handleGenerateDraft() {
    if (!draftForm.sectionId) return
    const result = await runAction('Minuta da seção', () => casesService.generateReportSectionDraft(caseId, draftForm.sectionId, {
      context: draftForm.context || undefined,
      instructions: draftForm.instructions || undefined,
      overwrite_existing: draftForm.overwrite,
    }))
    if (result) setDocumentToolResult(result)
  }

  async function handleCreateAttachment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedReportId) return
    const result = await runAction('Anexo/apêndice', () => casesService.createReportAttachment(caseId, selectedReportId, {
      attachment_type: attachmentForm.type,
      title: attachmentForm.title,
      description: attachmentForm.description || undefined,
      file_id: attachmentForm.fileId || undefined,
      calculation_version_id: attachmentForm.calculationVersionId || undefined,
    }))
    if (result) setAttachmentForm({ type: 'anexo', title: '', description: '', fileId: '', calculationVersionId: '' })
  }

  async function handleCreateClarification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const reportId = clarificationForm.reportId || selectedReportId
    if (!reportId) return
    const result = await runAction('Esclarecimento', () => casesService.createReportClarification(caseId, {
      report_id: reportId,
      theme: clarificationForm.theme,
      request_text: clarificationForm.request_text,
      preliminary_response: clarificationForm.preliminary_response || undefined,
      final_response: clarificationForm.final_response || undefined,
    }))
    if (result) setClarificationForm((prev) => ({ ...prev, theme: '', request_text: '', preliminary_response: '', final_response: '' }))
  }

  async function handleCreateFee(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = await runAction('Honorários', () => casesService.createFee(caseId, {
      proposed_amount: feeForm.proposed_amount ? Number(feeForm.proposed_amount) : undefined,
      arbitrated_amount: feeForm.arbitrated_amount ? Number(feeForm.arbitrated_amount) : undefined,
      deposited_amount: feeForm.deposited_amount ? Number(feeForm.deposited_amount) : undefined,
      withdrawn_amount: feeForm.withdrawn_amount ? Number(feeForm.withdrawn_amount) : undefined,
      status: feeForm.status,
      notes: feeForm.notes || undefined,
    }))
    if (result) setFeeForm({ proposed_amount: '', arbitrated_amount: '', deposited_amount: '', withdrawn_amount: '', status: 'proposto', notes: '' })
  }

  async function handleSemanticSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!semanticQuery.trim()) return
    const result = await runAction('Busca semântica', () => casesService.semanticSearch(semanticQuery.trim(), caseId), false)
    if (result) setSemanticResults(result)
  }

  async function handleChunkSearch() {
    if (!semanticQuery.trim()) return
    const result = await runAction('Busca em chunks', () => casesService.chunkSearch(semanticQuery.trim()), false)
    if (result) setChunkSearchResults(result)
  }

  async function handleProcessingJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!processingJobId.trim()) return
    const result = await runAction('Job de processamento', () => casesService.getProcessingJob(processingJobId.trim()), false)
    if (result) setProcessingJob(result)
  }

  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = await runAction('Usuário', () => authService.createUser({
      email: userForm.email,
      password: userForm.password,
      full_name: userForm.full_name,
      role: userForm.role as 'admin' | 'perito' | 'assistente' | 'visualizador',
    }), false)
    if (result) setUserForm({ email: '', password: '', full_name: '', role: 'assistente' })
  }

  async function handleSuggestions() {
    const result = await runAction('Sugestões de documentos', () => casesService.getDocumentSuggestions(caseId, suggestionContext), false)
    if (result) setSuggestions(result)
  }

  async function handleSummarizeDocument() {
    if (!selectedDocument) return
    const result = await runAction('Resumo IA do documento', () => casesService.summarizeDocument(selectedDocument.id), false)
    if (result) setAiOutput(result)
  }

  async function handleContradictions(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!contradictionMonth.trim()) return
    const result = await runAction('Comparação de contradições', () => casesService.compareDocumentContradictions(caseId, contradictionMonth.trim()), false)
    if (result) setContradictions(result)
  }

  function toggleEvidence(evidenceId: string) {
    setSelectedEvidenceIds((prev) =>
      prev.includes(evidenceId)
        ? prev.filter((item) => item !== evidenceId)
        : [...prev, evidenceId]
    )
  }

  const busy = (name: string) => busyAction === name

  return (
    <section className={styles.operations}>
      <div className={styles.toolbar}>
        <div>
          <p className={styles.eyebrow}>Operações do backend</p>
          <h2>Fluxo pericial completo</h2>
          <p>Execute os módulos técnicos do backend sem sair do processo.</p>
        </div>
        <button className={styles.ghostButton} type="button" onClick={loadAll} disabled={loading}>
          {loading ? <Loader2 className={styles.spin} size={17} /> : <RefreshCw size={17} />}
          Atualizar módulos
        </button>
      </div>

      {notice && (
        <div className={`${styles.notice} ${notice.tone === 'error' ? styles.noticeError : styles.noticeSuccess}`}>
          {notice.tone === 'error' ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          {notice.text}
        </div>
      )}

      <div className={styles.summaryGrid}>
        <span><strong>{documents.length}</strong>documentos</span>
        <span><strong>{quesitos.length}</strong>quesitos</span>
        <span><strong>{evidence.length}</strong>evidências</span>
        <span><strong>{matrix.length}</strong>matriz</span>
        <span><strong>{diligences.length}</strong>diligências</span>
        <span><strong>{reports.length}</strong>laudos</span>
        <span><strong>{fees.length}</strong>honorários</span>
      </div>

      <div className={styles.tabs} role="tablist" aria-label="Módulos periciais">
        {[
          ['documents', FileText, 'Documentos'],
          ['quesitos', ClipboardCheck, 'Quesitos'],
          ['evidence', ShieldCheck, 'Evidência e matriz'],
          ['diligences', Gavel, 'Diligências'],
          ['diary', NotebookPen, 'Diário e cálculos'],
          ['reports', ReceiptText, 'Laudos'],
          ['finance-ai', Bot, 'IA e honorários'],
        ].map(([tab, Icon, label]) => {
          const IconComponent = Icon as typeof FileText
          return (
            <button
              key={tab as string}
              className={activeTab === tab ? styles.tabActive : ''}
              type="button"
              onClick={() => setActiveTab(tab as OperationsTab)}
            >
              <IconComponent size={16} />
              {label as string}
            </button>
          )
        })}
      </div>

      {activeTab === 'documents' && (
        <div className={styles.workspace}>
          <div className={styles.grid}>
            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Documentos</p>
                  <h3>Ferramentas do PDF</h3>
                  <p>Integridade, páginas, OCR, preview, classificação e inventário.</p>
                </div>
              </div>
              <div className={styles.form}>
                <label>
                  Documento
                  <select value={selectedDocumentId} onChange={(event) => setSelectedDocumentId(event.target.value)}>
                    {documents.map((document) => (
                      <option key={document.id} value={document.id}>{document.display_name || document.original_filename}</option>
                    ))}
                  </select>
                </label>
                <div className={styles.actionRow}>
                  <button className={styles.button} type="button" onClick={handleLoadDocumentTools} disabled={!selectedDocument || busy('Consulta documental')}>
                    {busy('Consulta documental') ? <Loader2 className={styles.spin} size={16} /> : <RefreshCw size={16} />}
                    Consultar tudo
                  </button>
                  <button className={styles.ghostButton} type="button" onClick={() => selectedDocument && runAction('Integridade', () => casesService.checkDocumentIntegrity(caseId, selectedDocument.id), false).then((result) => result && setDocumentToolResult(result))}>
                    Verificar hash
                  </button>
                  <button className={styles.ghostButton} type="button" onClick={handleDownloadDocument}>
                    <Download size={16} />
                    Download original
                  </button>
                  <button className={styles.ghostButton} type="button" onClick={() => selectedDocument && runAction('Inventário documental', () => casesService.generateDocumentInventory(caseId, selectedDocument.id), false).then((result) => result && setDocumentInventory(result))}>
                    Gerar inventário
                  </button>
                </div>
                <form className={styles.form} onSubmit={handleProcessingJob}>
                  <label>
                    Consultar job de processamento por ID
                    <input value={processingJobId} onChange={(event) => setProcessingJobId(event.target.value)} placeholder="processing_job_id" />
                  </label>
                  <button className={styles.ghostButton} type="submit">Consultar job</button>
                </form>
                {filePages.length > 0 && (
                  <>
                    <label>
                      Página técnica
                      <select value={selectedFilePageId} onChange={(event) => setSelectedFilePageId(event.target.value)}>
                        {filePages.map((page) => (
                          <option key={page.id} value={page.id}>Página {page.page_number} · OCR {page.status_ocr}</option>
                        ))}
                      </select>
                    </label>
                    <div className={styles.formRow}>
                      <label>
                        Corrigir classe para
                        <select value={correctClass} onChange={(event) => setCorrectClass(event.target.value)}>
                          {DOCUMENT_CLASSES.map((item) => <option key={item} value={item}>{item}</option>)}
                        </select>
                      </label>
                    </div>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => handleFilePageAction('preview')}>Preview</button>
                      <button className={styles.ghostButton} type="button" onClick={() => handleFilePageAction('ocr')}>OCR da página</button>
                      <button className={styles.ghostButton} type="button" onClick={() => handleFilePageAction('classify')}>Classificar</button>
                      <button className={styles.ghostButton} type="button" onClick={() => handleFilePageAction('approve')}>Aprovar</button>
                      <button className={styles.ghostButton} type="button" onClick={() => handleFilePageAction('correct')}>Corrigir</button>
                    </div>
                  </>
                )}
              </div>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Resultado</p>
                  <h3>Retorno das ferramentas</h3>
                </div>
              </div>
              {documentInventory?.items.length ? (
                <div className={styles.list}>
                  {documentInventory.items.slice(0, 10).map((item) => (
                    <article className={styles.item} key={item.id}>
                      <div className={styles.itemHeader}>
                        <strong>{item.custom_label || item.document_class}</strong>
                        <span className={styles.badge}>p. {item.start_page}-{item.end_page}</span>
                      </div>
                      <small>{item.page_count} página(s) · {Math.round((item.confidence_avg ?? 0) * 100)}% confiança</small>
                      <div className={styles.actionRow}>
                        <button className={styles.ghostButton} type="button" onClick={() => selectedDocument && runAction('Marcação de relevância', () => casesService.updateDocumentInventoryItem(caseId, selectedDocument.id, item.id, { is_relevant: !item.is_relevant }), false).then(() => handleLoadDocumentTools())}>
                          {item.is_relevant ? 'Marcar irrelevante' : 'Marcar relevante'}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : ocrText ? (
                <div className={styles.resultBox}>
                  <strong>Página {ocrText.page_number} · {ocrText.blocks.length} bloco(s)</strong>
                  <pre>{ocrText.full_text.slice(0, 3000) || 'Sem texto extraído.'}</pre>
                </div>
              ) : processingJob ? (
                <div className={styles.resultBox}>
                  <strong>{processingJob.job_type} · {processingJob.status}</strong>
                  <pre>{JSON.stringify(processingJob, null, 2)}</pre>
                </div>
              ) : documentToolResult ? (
                <div className={styles.resultBox}>
                  <pre>{JSON.stringify(documentToolResult, null, 2)}</pre>
                </div>
              ) : (
                <div className={styles.empty}>Use as ações ao lado para consultar o backend documental.</div>
              )}
            </section>
          </div>
        </div>
      )}

      {activeTab === 'quesitos' && (
        <div className={styles.workspace}>
          <div className={styles.grid}>
            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Quesitos</p>
                  <h3>Criar, importar e responder</h3>
                </div>
              </div>
              <form className={styles.form} onSubmit={handleCreateQuesito}>
                <div className={styles.formRow}>
                  <label>Número<input value={quesitoForm.sequence} onChange={(event) => setQuesitoForm((prev) => ({ ...prev, sequence: event.target.value }))} /></label>
                  <label>Origem<input value={quesitoForm.origin} onChange={(event) => setQuesitoForm((prev) => ({ ...prev, origin: event.target.value }))} /></label>
                </div>
                <label>Texto<textarea rows={4} value={quesitoForm.text} onChange={(event) => setQuesitoForm((prev) => ({ ...prev, text: event.target.value }))} required /></label>
                <div className={styles.formRow}>
                  <label>Tema<input value={quesitoForm.tema} onChange={(event) => setQuesitoForm((prev) => ({ ...prev, tema: event.target.value }))} /></label>
                  <label>Tipo<input value={quesitoForm.tipo} onChange={(event) => setQuesitoForm((prev) => ({ ...prev, tipo: event.target.value }))} /></label>
                </div>
                <button className={styles.button} type="submit" disabled={busy('Quesito')}>Criar quesito</button>
              </form>

              <form className={styles.form} onSubmit={handleImportQuesitos}>
                <label>Importar em lote<textarea rows={4} value={batchQuesitos} onChange={(event) => setBatchQuesitos(event.target.value)} placeholder="Um quesito por linha" /></label>
                <button className={styles.ghostButton} type="submit">Importar linhas</button>
              </form>

              <form className={styles.form} onSubmit={handleCreateAnswer}>
                <label>
                  Quesito selecionado
                  <select value={selectedQuesitoId} onChange={(event) => setSelectedQuesitoId(event.target.value)}>
                    {quesitos.map((quesito) => <option key={quesito.id} value={quesito.id}>#{quesito.sequence_number} {quesito.question_text.slice(0, 70)}</option>)}
                  </select>
                </label>
                <label>Resposta manual<textarea rows={4} value={answerText} onChange={(event) => setAnswerText(event.target.value)} /></label>
                <div className={styles.actionRow}>
                  <button className={styles.button} type="submit">Salvar resposta</button>
                  <button className={styles.ghostButton} type="button" onClick={() => handleQuesitoAI('answer')}>Gerar resposta IA</button>
                  <button className={styles.ghostButton} type="button" onClick={() => handleQuesitoAI('draft')}>Minuta com evidências</button>
                  <button className={styles.ghostButton} type="button" onClick={() => firstEvidenceId && selectedQuesitoId && runAction('Vínculo quesito-evidência', () => casesService.linkQuesitoEvidence(caseId, selectedQuesitoId, firstEvidenceId))}>Vincular 1ª evidência</button>
                  <button className={styles.ghostButton} type="button" onClick={() => handleQuesitoAI('evidence')}>Listar evidências</button>
                </div>
              </form>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Lista</p>
                  <h3>{quesitos.length} quesito(s)</h3>
                </div>
              </div>
              <div className={styles.list}>
                {quesitos.map((quesito) => (
                  <article className={styles.item} key={quesito.id}>
                    <div className={styles.itemHeader}>
                      <strong>#{quesito.sequence_number} · {quesito.origin}</strong>
                      <span className={styles.badge}>{quesito.status}</span>
                    </div>
                    <p>{quesito.question_text}</p>
                    <small>{quesito.answers?.length ?? 0} resposta(s) · {quesito.tema || 'sem tema'}</small>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Status do quesito', () => casesService.updateQuesito(caseId, quesito.id, { status: 'respondido' } as Partial<Quesito>))}>Marcar respondido</button>
                    </div>
                  </article>
                ))}
                {quesitos.length === 0 && <div className={styles.empty}>Nenhum quesito cadastrado.</div>}
              </div>
              {(questionDraft || qEvidence.length > 0) && (
                <div className={styles.resultBox}>
                  <pre>{JSON.stringify(questionDraft || qEvidence, null, 2)}</pre>
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {activeTab === 'evidence' && (
        <div className={styles.workspace}>
          <div className={styles.grid}>
            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Evidência</p>
                  <h3>Criar trecho probatório</h3>
                </div>
              </div>
              <form className={styles.form} onSubmit={handleCreateEvidence}>
                <label>Documento<select value={evidenceForm.documentId} onChange={(event) => setEvidenceForm((prev) => ({ ...prev, documentId: event.target.value }))}>{documents.map((document) => <option key={document.id} value={document.id}>{document.display_name || document.original_filename}</option>)}</select></label>
                <div className={styles.formRow}>
                  <label>Página<input type="number" min="1" value={evidenceForm.page} onChange={(event) => setEvidenceForm((prev) => ({ ...prev, page: event.target.value }))} /></label>
                  <label>Tipo<select value={evidenceForm.type} onChange={(event) => setEvidenceForm((prev) => ({ ...prev, type: event.target.value }))}>{EVIDENCE_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
                </div>
                <label>Trecho<textarea rows={4} value={evidenceForm.text} onChange={(event) => setEvidenceForm((prev) => ({ ...prev, text: event.target.value }))} required /></label>
                <div className={styles.formRow}>
                  <label>Confiabilidade<input type="number" min="1" max="5" value={evidenceForm.reliability} onChange={(event) => setEvidenceForm((prev) => ({ ...prev, reliability: event.target.value }))} /></label>
                  <label>Observações<input value={evidenceForm.notes} onChange={(event) => setEvidenceForm((prev) => ({ ...prev, notes: event.target.value }))} /></label>
                </div>
                <button className={styles.button} type="submit">Criar evidência</button>
              </form>

              <form className={styles.form} onSubmit={handleCreateMatrix}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.eyebrow}>Matriz de prova</p>
                    <h3>Fato controvertido</h3>
                  </div>
                </div>
                <label>Fato<input value={matrixForm.disputed_fact} onChange={(event) => setMatrixForm((prev) => ({ ...prev, disputed_fact: event.target.value }))} required /></label>
                <label>Tema<input value={matrixForm.theme} onChange={(event) => setMatrixForm((prev) => ({ ...prev, theme: event.target.value }))} required /></label>
                <label>Procedimento<input value={matrixForm.expert_procedure} onChange={(event) => setMatrixForm((prev) => ({ ...prev, expert_procedure: event.target.value }))} /></label>
                <label>Metodologia<textarea rows={2} value={matrixForm.methodology_or_criteria} onChange={(event) => setMatrixForm((prev) => ({ ...prev, methodology_or_criteria: event.target.value }))} /></label>
                <label>Resultado<textarea rows={2} value={matrixForm.result_found} onChange={(event) => setMatrixForm((prev) => ({ ...prev, result_found: event.target.value }))} /></label>
                <label>Impacto<textarea rows={2} value={matrixForm.technical_impact} onChange={(event) => setMatrixForm((prev) => ({ ...prev, technical_impact: event.target.value }))} /></label>
                <div className={styles.checkboxList}>
                  {evidence.map((item) => (
                    <label key={item.id}>
                      <input type="checkbox" checked={selectedEvidenceIds.includes(item.id)} onChange={() => toggleEvidence(item.id)} />
                      p. {item.page_number} · {item.text_excerpt.slice(0, 90)}
                    </label>
                  ))}
                </div>
                <button className={styles.button} type="submit" disabled={selectedEvidenceIds.length === 0}>Criar item da matriz</button>
              </form>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Provas</p>
                  <h3>Evidências e matriz</h3>
                </div>
              </div>
              <div className={styles.list}>
                {evidence.map((item) => (
                  <article className={styles.item} key={item.id}>
                    <div className={styles.itemHeader}>
                      <strong>{item.evidence_type} · p. {item.page_number}</strong>
                      <span className={styles.badge}>{item.validation_status}</span>
                    </div>
                    <p>{item.text_excerpt}</p>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Validação de evidência', () => casesService.validateEvidence(item.id))}>Validar</button>
                      <button className={styles.dangerButton} type="button" onClick={() => runAction('Rejeição de evidência', () => casesService.rejectEvidence(item.id, 'Rejeitado pela revisão da interface'))}>Rejeitar</button>
                    </div>
                  </article>
                ))}
                {matrix.map((item) => (
                  <article className={styles.item} key={item.id}>
                    <div className={styles.itemHeader}>
                      <strong>{item.theme}</strong>
                      <span className={styles.badge}>{item.status}</span>
                    </div>
                    <p>{item.disputed_fact}</p>
                    <small>{item.evidence_ids.length} evidência(s) vinculada(s)</small>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Validação da matriz', () => casesService.validateEvidenceMatrix(item.id), false).then((result) => result && setMatrixValidation(result))}>Validar matriz</button>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Publicação da matriz', () => casesService.updateEvidenceMatrix(caseId, item.id, { status: 'published' }))}>Publicar</button>
                      <button className={styles.dangerButton} type="button" onClick={() => runAction('Exclusão da matriz', () => casesService.deleteEvidenceMatrix(item.id))}><Trash2 size={16} />Excluir</button>
                    </div>
                  </article>
                ))}
                {evidence.length === 0 && matrix.length === 0 && <div className={styles.empty}>Nenhuma evidência ou matriz cadastrada.</div>}
              </div>
              {matrixValidation && <div className={styles.resultBox}><pre>{JSON.stringify(matrixValidation, null, 2)}</pre></div>}
            </section>
          </div>
        </div>
      )}

      {activeTab === 'diligences' && (
        <div className={styles.workspace}>
          <div className={styles.grid}>
            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Diligências</p>
                  <h3>Solicitações e limitações</h3>
                </div>
              </div>
              <form className={styles.form} onSubmit={handleCreateDiligence}>
                <div className={styles.formRow}>
                  <label>Número<input value={diligenceForm.number} onChange={(event) => setDiligenceForm((prev) => ({ ...prev, number: event.target.value }))} /></label>
                  <label>Prazo<input type="datetime-local" value={diligenceForm.deadline} onChange={(event) => setDiligenceForm((prev) => ({ ...prev, deadline: event.target.value }))} /></label>
                </div>
                <label>Destinatário<input value={diligenceForm.recipient} onChange={(event) => setDiligenceForm((prev) => ({ ...prev, recipient: event.target.value }))} required /></label>
                <label>Documento solicitado<input value={diligenceForm.requested_document} onChange={(event) => setDiligenceForm((prev) => ({ ...prev, requested_document: event.target.value }))} required /></label>
                <label>Período<input value={diligenceForm.period} onChange={(event) => setDiligenceForm((prev) => ({ ...prev, period: event.target.value }))} required /></label>
                <label>Justificativa técnica<textarea rows={3} value={diligenceForm.technical_justification} onChange={(event) => setDiligenceForm((prev) => ({ ...prev, technical_justification: event.target.value }))} required /></label>
                <label>Observações<textarea rows={2} value={diligenceForm.observations} onChange={(event) => setDiligenceForm((prev) => ({ ...prev, observations: event.target.value }))} /></label>
                <button className={styles.button} type="submit">Criar diligência</button>
              </form>

              <form className={styles.form} onSubmit={handleCreateLimitation}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.eyebrow}>Limitação técnica</p>
                    <h3>Registrar obstáculo</h3>
                  </div>
                </div>
                <label>Tipo<input value={limitationForm.type} onChange={(event) => setLimitationForm((prev) => ({ ...prev, type: event.target.value }))} required /></label>
                <label>Descrição<textarea rows={3} value={limitationForm.description} onChange={(event) => setLimitationForm((prev) => ({ ...prev, description: event.target.value }))} required /></label>
                <label>Impacto técnico<textarea rows={3} value={limitationForm.technical_impact} onChange={(event) => setLimitationForm((prev) => ({ ...prev, technical_impact: event.target.value }))} required /></label>
                <label>Criticidade<select value={limitationForm.criticality} onChange={(event) => setLimitationForm((prev) => ({ ...prev, criticality: event.target.value }))}>{['baixa', 'média', 'alta', 'crítica'].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <button className={styles.button} type="submit">Criar limitação</button>
              </form>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Controle</p>
                  <h3>Diligências e limitações</h3>
                </div>
              </div>
              <div className={styles.list}>
                {diligences.map((item) => (
                  <article className={styles.item} key={item.id}>
                    <div className={styles.itemHeader}>
                      <strong>{item.number} · {item.recipient}</strong>
                      <span className={styles.badge}>{item.status}</span>
                    </div>
                    <small>Prazo {new Date(item.deadline).toLocaleString('pt-BR')}</small>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => handleSelectDiligence(item.id)}>Ver itens</button>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('DOCX da diligência', () => casesService.downloadDiligenceDocx(item.id), false).then((blob) => blob && saveBlob(blob, `termo_diligencia_${item.number}.docx`))}><Download size={16} />DOCX</button>
                      <button className={styles.dangerButton} type="button" onClick={() => runAction('Exclusão da diligência', () => casesService.deleteDiligence(item.id))}>Excluir</button>
                    </div>
                  </article>
                ))}
                {selectedDiligence?.items?.map((item) => (
                  <article className={styles.item} key={item.id}>
                    <strong>Item: {item.requested_document}</strong>
                    <p>{item.technical_justification}</p>
                    <small>{item.period} · {item.status_recebimento}</small>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => setReceiptForm((prev) => ({ ...prev, itemId: item.id }))}>Selecionar recebimento</button>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Limitação da diligência', () => casesService.createLimitationFromDiligenceItem(item.id))}>Gerar limitação</button>
                    </div>
                  </article>
                ))}
                {limitations.map((item) => (
                  <article className={styles.item} key={item.id}>
                    <div className={styles.itemHeader}>
                      <strong>{item.type}</strong>
                      <span className={styles.badge}>{item.criticality}</span>
                    </div>
                    <p>{item.description}</p>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Resolução da limitação', () => casesService.updateTechnicalLimitation(caseId, item.id, { status: 'resolved' }))}>Resolver</button>
                      <button className={styles.dangerButton} type="button" onClick={() => runAction('Exclusão da limitação', () => casesService.deleteTechnicalLimitation(item.id))}>Excluir</button>
                    </div>
                  </article>
                ))}
              </div>
              {selectedDiligence && (
                <form className={styles.form} onSubmit={(event) => {
                  event.preventDefault()
                  if (!receiptForm.itemId) return
                  runAction('Recebimento de diligência', () => casesService.registerDiligenceReceipt(selectedDiligence.id, receiptForm.itemId, {
                    documento_recebido_id: receiptForm.documentId,
                    status_recebimento: receiptForm.status,
                    observacao_pendencia: receiptForm.note || undefined,
                  })).then(() => handleSelectDiligence(selectedDiligence.id))
                }}>
                  <label>Item<select value={receiptForm.itemId} onChange={(event) => setReceiptForm((prev) => ({ ...prev, itemId: event.target.value }))}>{selectedDiligence.items?.map((item) => <option key={item.id} value={item.id}>{item.requested_document}</option>)}</select></label>
                  <label>Documento recebido<select value={receiptForm.documentId} onChange={(event) => setReceiptForm((prev) => ({ ...prev, documentId: event.target.value }))}>{documents.map((document) => <option key={document.id} value={document.id}>{document.display_name || document.original_filename}</option>)}</select></label>
                  <label>Status<select value={receiptForm.status} onChange={(event) => setReceiptForm((prev) => ({ ...prev, status: event.target.value }))}>{['recebido', 'parcial', 'não_recebido'].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                  <label>Observação<input value={receiptForm.note} onChange={(event) => setReceiptForm((prev) => ({ ...prev, note: event.target.value }))} /></label>
                  <button className={styles.button} type="submit">Registrar recebimento</button>
                </form>
              )}
            </section>
          </div>
        </div>
      )}

      {activeTab === 'diary' && (
        <div className={styles.workspace}>
          <div className={styles.grid}>
            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Diário técnico</p>
                  <h3>Decisões e cálculos</h3>
                </div>
              </div>
              <form className={styles.form} onSubmit={handleCreateDiary}>
                <div className={styles.formRow}>
                  <label>Data<input type="date" value={diaryForm.entry_date} onChange={(event) => setDiaryForm((prev) => ({ ...prev, entry_date: event.target.value }))} /></label>
                  <label>Tipo de decisão<input value={diaryForm.decision_type} onChange={(event) => setDiaryForm((prev) => ({ ...prev, decision_type: event.target.value }))} required /></label>
                </div>
                <label>Descrição<textarea rows={3} value={diaryForm.description} onChange={(event) => setDiaryForm((prev) => ({ ...prev, description: event.target.value }))} required /></label>
                <label>Justificativa<textarea rows={3} value={diaryForm.technical_justification} onChange={(event) => setDiaryForm((prev) => ({ ...prev, technical_justification: event.target.value }))} required /></label>
                <button className={styles.button} type="submit">Registrar decisão</button>
              </form>

              <form className={styles.form} onSubmit={handleCreateCalculation}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.eyebrow}>Cálculo</p>
                    <h3>Controle e versão</h3>
                  </div>
                </div>
                <label>Tipo<input value={calculationForm.calculation_type} onChange={(event) => setCalculationForm((prev) => ({ ...prev, calculation_type: event.target.value }))} required /></label>
                <label>Descrição<textarea rows={2} value={calculationForm.description} onChange={(event) => setCalculationForm((prev) => ({ ...prev, description: event.target.value }))} /></label>
                <button className={styles.button} type="submit"><Calculator size={16} />Criar controle</button>
              </form>

              <form className={styles.form} onSubmit={handleUploadCalculationVersion}>
                <label>Controle<select value={selectedCalculationId} onChange={(event) => setSelectedCalculationId(event.target.value)}>{createdCalculations.map((item) => <option key={item.id} value={item.id}>{item.calculation_type} · {shortId(item.id)}</option>)}</select></label>
                <label>Arquivo<input type="file" onChange={(event) => setCalculationFile(event.target.files?.[0] ?? null)} /></label>
                <label>Premissas<textarea rows={2} value={calculationVersionForm.premises} onChange={(event) => setCalculationVersionForm((prev) => ({ ...prev, premises: event.target.value }))} /></label>
                <label>Metodologia<textarea rows={2} value={calculationVersionForm.methodology} onChange={(event) => setCalculationVersionForm((prev) => ({ ...prev, methodology: event.target.value }))} /></label>
                <button className={styles.button} type="submit" disabled={!selectedCalculationId || !calculationFile}>Enviar versão</button>
              </form>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Histórico técnico</p>
                  <h3>Decisões, cálculos e vínculos</h3>
                </div>
              </div>
              <div className={styles.list}>
                {diary.map((entry) => (
                  <article className={styles.item} key={entry.id}>
                    <div className={styles.itemHeader}>
                      <strong>{entry.decision_type}</strong>
                      <span className={styles.badge}>{entry.status}</span>
                    </div>
                    <p>{entry.description}</p>
                    <small>{entry.entry_date}</small>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => firstEvidenceId && runAction('Vínculo diário-evidência', () => casesService.linkTechnicalDiaryEvidence(caseId, entry.id, firstEvidenceId))}>Vincular 1ª evidência</button>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Publicação do diário', () => casesService.updateTechnicalDiaryEntry(caseId, entry.id, { status: 'published' }))}>Publicar</button>
                      <button className={styles.dangerButton} type="button" onClick={() => runAction('Exclusão do diário', () => casesService.deleteTechnicalDiaryEntry(entry.id))}>Excluir</button>
                    </div>
                  </article>
                ))}
                {createdCalculations.map((item) => (
                  <article className={styles.item} key={item.id}>
                    <strong>{item.calculation_type}</strong>
                    <small>{item.status} · {shortId(item.id)}</small>
                  </article>
                ))}
                {calculationVersions.map((version) => (
                  <article className={styles.item} key={version.id}>
                    <strong>{version.original_filename}</strong>
                    <small>v{version.version_number} · {shortId(version.id)}</small>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => firstEvidenceId && runAction('Vínculo cálculo-evidência', () => casesService.linkCalculationEvidence(caseId, version.id, firstEvidenceId))}>Vincular 1ª evidência</button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}

      {activeTab === 'reports' && (
        <div className={styles.workspace}>
          <div className={styles.grid}>
            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Laudos</p>
                  <h3>Estrutura, checklist e anexos</h3>
                </div>
              </div>
              <form className={styles.form} onSubmit={handleCreateReport}>
                <label>Título<input value={reportForm.title} onChange={(event) => setReportForm((prev) => ({ ...prev, title: event.target.value }))} required /></label>
                <div className={styles.formRow}>
                  <label>Tipo<input value={reportForm.report_type} onChange={(event) => setReportForm((prev) => ({ ...prev, report_type: event.target.value }))} /></label>
                  <label>Status<input value={reportForm.status} onChange={(event) => setReportForm((prev) => ({ ...prev, status: event.target.value }))} /></label>
                </div>
                <button className={styles.button} type="submit">Criar laudo</button>
              </form>

              <div className={styles.form}>
                <label>Laudo selecionado<select value={selectedReportId} onChange={(event) => setSelectedReportId(event.target.value)}>{reports.map((report) => <option key={report.id} value={report.id}>{report.title}</option>)}</select></label>
                <div className={styles.actionRow}>
                  <button className={styles.ghostButton} type="button" disabled={!selectedReportId} onClick={() => selectedReportId && runAction('Checklist do laudo', () => casesService.generateReportChecklist(caseId, selectedReportId), false).then((result) => result && setReportChecklist(result))}>Gerar checklist</button>
                  <button className={styles.ghostButton} type="button" disabled={!selectedReportId} onClick={() => selectedReportId && runAction('Validação de exportação', () => casesService.validateReportChecklistExport(caseId, selectedReportId), false).then((result) => result && setReportChecklistValidation(result))}>Validar exportação</button>
                  <button className={styles.ghostButton} type="button" disabled={!selectedReportId} onClick={() => selectedReportId && runAction('DOCX do laudo', () => casesService.downloadReportDocx(selectedReportId), false).then((blob) => blob && saveBlob(blob, `laudo_${shortId(selectedReportId)}.docx`))}><Download size={16} />DOCX</button>
                  <button className={styles.dangerButton} type="button" disabled={!selectedReportId} onClick={() => selectedReportId && runAction('Exclusão do laudo', () => casesService.deleteReport(selectedReportId))}>Excluir laudo</button>
                </div>
              </div>

              <form className={styles.form} onSubmit={handleCreateSection}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.eyebrow}>Seção</p>
                    <h3>Adicionar seção</h3>
                  </div>
                </div>
                <div className={styles.formRow}>
                  <label>Ordem<input type="number" min="1" value={sectionForm.section_order} onChange={(event) => setSectionForm((prev) => ({ ...prev, section_order: event.target.value }))} /></label>
                  <label>Status<input value={sectionForm.review_status} onChange={(event) => setSectionForm((prev) => ({ ...prev, review_status: event.target.value }))} /></label>
                </div>
                <label>Título<input value={sectionForm.title} onChange={(event) => setSectionForm((prev) => ({ ...prev, title: event.target.value }))} required /></label>
                <label>Conteúdo<textarea rows={4} value={sectionForm.content} onChange={(event) => setSectionForm((prev) => ({ ...prev, content: event.target.value }))} /></label>
                <button className={styles.button} type="submit" disabled={!selectedReportId}>Criar seção</button>
              </form>

              <form className={styles.form} onSubmit={handleCreateAttachment}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.eyebrow}>Anexo ou apêndice</p>
                    <h3>Vincular material</h3>
                  </div>
                </div>
                <div className={styles.formRow}>
                  <label>Tipo<select value={attachmentForm.type} onChange={(event) => setAttachmentForm((prev) => ({ ...prev, type: event.target.value }))}><option value="anexo">anexo</option><option value="apendice">apêndice</option></select></label>
                  <label>Arquivo<select value={attachmentForm.fileId} onChange={(event) => setAttachmentForm((prev) => ({ ...prev, fileId: event.target.value, calculationVersionId: '' }))}><option value="">sem arquivo</option>{documents.map((doc) => <option key={doc.id} value={doc.id}>{doc.display_name || doc.original_filename}</option>)}</select></label>
                </div>
                <label>Título<input value={attachmentForm.title} onChange={(event) => setAttachmentForm((prev) => ({ ...prev, title: event.target.value }))} required /></label>
                <label>Descrição<input value={attachmentForm.description} onChange={(event) => setAttachmentForm((prev) => ({ ...prev, description: event.target.value }))} /></label>
                <button className={styles.button} type="submit" disabled={!selectedReportId}>Criar anexo</button>
              </form>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Laudo ativo</p>
                  <h3>{selectedReport?.title || 'Nenhum laudo selecionado'}</h3>
                </div>
              </div>
              <div className={styles.list}>
                {reportSections.map((section) => (
                  <article className={styles.item} key={section.id}>
                    <div className={styles.itemHeader}>
                      <strong>{section.section_order}. {section.title}</strong>
                      <span className={styles.badge}>{section.review_status}</span>
                    </div>
                    <p>{section.content.slice(0, 260) || 'Sem conteúdo.'}</p>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => setDraftForm((prev) => ({ ...prev, sectionId: section.id }))}>Selecionar para minuta</button>
                      <button className={styles.ghostButton} type="button" onClick={() => matrix[0] && runAction('Vínculo seção-matriz', () => casesService.linkReportSectionMatrix(caseId, section.id, matrix[0].id))}>Vincular 1ª matriz</button>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Revisão da seção', () => casesService.updateReportSection(caseId, section.id, { review_status: 'revisado' }))}>Marcar revisada</button>
                      <button className={styles.dangerButton} type="button" onClick={() => runAction('Exclusão da seção', () => casesService.deleteReportSection(caseId, section.id))}>Excluir</button>
                    </div>
                  </article>
                ))}
              </div>

              <div className={styles.form}>
                <label>Seção para minuta<select value={draftForm.sectionId} onChange={(event) => setDraftForm((prev) => ({ ...prev, sectionId: event.target.value }))}>{reportSections.map((section) => <option key={section.id} value={section.id}>{section.title}</option>)}</select></label>
                <label>Contexto<textarea rows={2} value={draftForm.context} onChange={(event) => setDraftForm((prev) => ({ ...prev, context: event.target.value }))} /></label>
                <label>Instruções<textarea rows={2} value={draftForm.instructions} onChange={(event) => setDraftForm((prev) => ({ ...prev, instructions: event.target.value }))} /></label>
                <label><input type="checkbox" checked={draftForm.overwrite} onChange={(event) => setDraftForm((prev) => ({ ...prev, overwrite: event.target.checked }))} /> Sobrescrever conteúdo</label>
                <button className={styles.button} type="button" onClick={handleGenerateDraft}>Gerar minuta IA</button>
              </div>

              {reportChecklist && (
                <div className={styles.list}>
                  {reportChecklist.items.slice(0, 8).map((item) => (
                    <article className={styles.item} key={item.id}>
                      <div className={styles.itemHeader}>
                        <strong>{item.title}</strong>
                        <span className={styles.badge}>{item.status}</span>
                      </div>
                      <button className={styles.ghostButton} type="button" onClick={() => selectedReportId && runAction('Checklist item', () => casesService.updateReportChecklistItem(caseId, selectedReportId, item.id, { status: 'completo' }), false).then(() => loadReportWorkspace(selectedReportId))}>Marcar completo</button>
                    </article>
                  ))}
                </div>
              )}

              {reportChecklistValidation && <div className={styles.resultBox}><pre>{JSON.stringify(reportChecklistValidation, null, 2)}</pre></div>}
              {reportAttachments.length > 0 && <div className={styles.resultBox}><strong>Anexos: {reportAttachments.length}</strong></div>}
            </section>
          </div>

          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <p className={styles.eyebrow}>Esclarecimentos</p>
                <h3>Pedidos vinculados ao laudo</h3>
              </div>
            </div>
            <form className={styles.form} onSubmit={handleCreateClarification}>
              <div className={styles.formRow}>
                <label>Laudo<select value={clarificationForm.reportId || selectedReportId} onChange={(event) => setClarificationForm((prev) => ({ ...prev, reportId: event.target.value }))}>{reports.map((report) => <option key={report.id} value={report.id}>{report.title}</option>)}</select></label>
                <label>Tema<input value={clarificationForm.theme} onChange={(event) => setClarificationForm((prev) => ({ ...prev, theme: event.target.value }))} required /></label>
              </div>
              <label>Pedido<textarea rows={3} value={clarificationForm.request_text} onChange={(event) => setClarificationForm((prev) => ({ ...prev, request_text: event.target.value }))} required /></label>
              <label>Resposta preliminar<textarea rows={2} value={clarificationForm.preliminary_response} onChange={(event) => setClarificationForm((prev) => ({ ...prev, preliminary_response: event.target.value }))} /></label>
              <button className={styles.button} type="submit" disabled={!selectedReportId && !clarificationForm.reportId}>Criar esclarecimento</button>
            </form>
            <div className={styles.list}>
              {clarifications.map((item) => (
                <article className={styles.item} key={item.id}>
                  <div className={styles.itemHeader}>
                    <strong>{item.theme}</strong>
                    <span className={styles.badge}>{item.status}</span>
                  </div>
                  <p>{item.request_text}</p>
                  <div className={styles.actionRow}>
                    <button className={styles.ghostButton} type="button" onClick={() => runAction('Esclarecimento respondido', () => casesService.updateReportClarification(caseId, item.id, { status: 'respondido' }))}>Marcar respondido</button>
                    <button className={styles.dangerButton} type="button" onClick={() => runAction('Exclusão do esclarecimento', () => casesService.deleteReportClarification(item.id))}>Excluir</button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      )}

      {activeTab === 'finance-ai' && (
        <div className={styles.workspace}>
          <div className={styles.grid}>
            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Honorários</p>
                  <h3>Valores da perícia</h3>
                </div>
              </div>
              <form className={styles.form} onSubmit={handleCreateFee}>
                <div className={styles.formRow}>
                  <label>Proposto<input type="number" min="0" step="0.01" value={feeForm.proposed_amount} onChange={(event) => setFeeForm((prev) => ({ ...prev, proposed_amount: event.target.value }))} /></label>
                  <label>Arbitrado<input type="number" min="0" step="0.01" value={feeForm.arbitrated_amount} onChange={(event) => setFeeForm((prev) => ({ ...prev, arbitrated_amount: event.target.value }))} /></label>
                </div>
                <div className={styles.formRow}>
                  <label>Depositado<input type="number" min="0" step="0.01" value={feeForm.deposited_amount} onChange={(event) => setFeeForm((prev) => ({ ...prev, deposited_amount: event.target.value }))} /></label>
                  <label>Levantado<input type="number" min="0" step="0.01" value={feeForm.withdrawn_amount} onChange={(event) => setFeeForm((prev) => ({ ...prev, withdrawn_amount: event.target.value }))} /></label>
                </div>
                <label>Status<input value={feeForm.status} onChange={(event) => setFeeForm((prev) => ({ ...prev, status: event.target.value }))} /></label>
                <label>Notas<textarea rows={2} value={feeForm.notes} onChange={(event) => setFeeForm((prev) => ({ ...prev, notes: event.target.value }))} /></label>
                <button className={styles.button} type="submit">Registrar honorários</button>
              </form>

              <form className={styles.form} onSubmit={handleSemanticSearch}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.eyebrow}>IA</p>
                    <h3>Busca, resumo e sugestões</h3>
                  </div>
                </div>
                <label>Busca semântica<input value={semanticQuery} onChange={(event) => setSemanticQuery(event.target.value)} placeholder="ex.: jornada, horas extras, adicional" /></label>
                <div className={styles.actionRow}>
                  <button className={styles.button} type="submit"><Search size={16} />Buscar IA</button>
                  <button className={styles.ghostButton} type="button" onClick={handleChunkSearch}>Buscar /search</button>
                </div>
              </form>
              <div className={styles.form}>
                <label>Contexto para documentos faltantes<textarea rows={2} value={suggestionContext} onChange={(event) => setSuggestionContext(event.target.value)} /></label>
                <div className={styles.actionRow}>
                  <button className={styles.ghostButton} type="button" onClick={handleSuggestions}>Sugerir documentos</button>
                  <button className={styles.ghostButton} type="button" onClick={handleSummarizeDocument} disabled={!selectedDocument}>Resumir documento selecionado</button>
                  {aiOutput && <button className={styles.ghostButton} type="button" onClick={() => runAction('Revisão IA', () => casesService.reviewAIOutput(aiOutput.id, { review_status: 'approved', review_note: 'Aprovado pela interface.' }), false).then((result) => result && setAiOutput(result))}>Aprovar saída IA</button>}
                </div>
              </div>
              <form className={styles.form} onSubmit={handleContradictions}>
                <label>Competência para contradições MM/AAAA<input value={contradictionMonth} onChange={(event) => setContradictionMonth(event.target.value)} placeholder="05/2026" /></label>
                <button className={styles.ghostButton} type="submit">Comparar holerite x ficha</button>
              </form>

              <form className={styles.form} onSubmit={handleCreateUser}>
                <div className={styles.panelHeader}>
                  <div>
                    <p className={styles.eyebrow}>Admin</p>
                    <h3>Criar usuário</h3>
                  </div>
                </div>
                <label>Nome<input value={userForm.full_name} onChange={(event) => setUserForm((prev) => ({ ...prev, full_name: event.target.value }))} required /></label>
                <label>Email<input type="email" value={userForm.email} onChange={(event) => setUserForm((prev) => ({ ...prev, email: event.target.value }))} required /></label>
                <div className={styles.formRow}>
                  <label>Senha<input type="password" value={userForm.password} onChange={(event) => setUserForm((prev) => ({ ...prev, password: event.target.value }))} required /></label>
                  <label>Perfil<select value={userForm.role} onChange={(event) => setUserForm((prev) => ({ ...prev, role: event.target.value }))}>{['admin', 'perito', 'assistente', 'visualizador'].map((role) => <option key={role} value={role}>{role}</option>)}</select></label>
                </div>
                <button className={styles.ghostButton} type="submit">Criar usuário</button>
              </form>
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeader}>
                <div>
                  <p className={styles.eyebrow}>Resultados</p>
                  <h3>Financeiro e IA</h3>
                </div>
              </div>
              <div className={styles.list}>
                {fees.map((fee) => (
                  <article className={styles.item} key={fee.id}>
                    <div className={styles.itemHeader}>
                      <strong>{money(fee.proposed_amount)} proposto</strong>
                      <span className={styles.badge}>{fee.status}</span>
                    </div>
                    <small>Arbitrado {money(fee.arbitrated_amount)} · depositado {money(fee.deposited_amount)}</small>
                    <div className={styles.actionRow}>
                      <button className={styles.ghostButton} type="button" onClick={() => runAction('Honorários depositados', () => casesService.updateFee(caseId, fee.id, { status: 'depositado' }))}>Marcar depositado</button>
                      <button className={styles.dangerButton} type="button" onClick={() => runAction('Exclusão de honorários', () => casesService.deleteFee(fee.id))}>Excluir</button>
                    </div>
                  </article>
                ))}
                {semanticResults.map((result) => (
                  <article className={styles.item} key={`${result.page_id}-${result.chunk_text.slice(0, 20)}`}>
                    <strong>Busca · p. {result.page_number}</strong>
                    <p>{result.chunk_text}</p>
                    <small>{Math.round(result.similarity * 100)}% similaridade</small>
                  </article>
                ))}
                {chunkSearchResults?.results.map((result) => (
                  <article className={styles.item} key={result.chunk_id}>
                    <strong>/search · p. {result.page_number}</strong>
                    <p>{result.text}</p>
                    <small>{Math.round(result.similarity * 100)}% similaridade</small>
                  </article>
                ))}
              </div>
              {(suggestions || aiOutput || contradictions) && (
                <div className={styles.resultBox}>
                  <pre>{JSON.stringify(suggestions || aiOutput || contradictions, null, 2)}</pre>
                </div>
              )}
            </section>
          </div>
        </div>
      )}
    </section>
  )
}
