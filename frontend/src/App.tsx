import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  FileUp,
  FileSearch,
  Loader2,
  LogOut,
  PlayCircle,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react'
import { CaseOperationsPanel } from './components/CaseOperations/CaseOperationsPanel'
import { DashboardPage } from './components/Dashboard/DashboardPage'
import { authService } from './services/auth'
import { casesService } from './services/cases'
import { extractErrorMessage } from './services/api'
import type {
  Case,
  CaseType,
  Document,
  DocumentAnalysisSummary,
  DocumentInventory,
  DocumentProcessingProgress,
  OCRSearchResult,
  User,
} from './types'
import styles from './App.module.css'

type View = 'dashboard' | 'cases' | 'case-detail'
type Notice = { tone: 'success' | 'error'; text: string } | null

const CASE_TYPES: CaseType[] = ['trabalhista', 'civel', 'fiscal', 'extrajudicial', 'arbitragem']

const INITIAL_CASE_FORM = {
  case_number: '',
  case_type: 'trabalhista' as CaseType,
  title: '',
  court: '',
  deadline_date: '',
  description: '',
  party_name: '',
  party_role: '',
}

const INITIAL_CASE_EDIT_FORM = {
  case_number: '',
  case_type: 'trabalhista' as CaseType,
  title: '',
  court: '',
  deadline_date: '',
  description: '',
  status: 'planejamento' as Case['status'],
}

function formatDate(value?: string) {
  if (!value) return 'Sem prazo'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('pt-BR').format(date)
}

function formatBytes(value: number) {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

function formatNumber(value?: number) {
  return new Intl.NumberFormat('pt-BR').format(value ?? 0)
}

function documentStatusLabel(status: Document['status']) {
  const labels: Record<string, string> = {
    uploaded: 'Recebido',
    hashing: 'Calculando hash',
    queued_ocr: 'Na fila de OCR',
    ocr_running: 'OCR em andamento',
    ocr_completed: 'OCR concluído',
    ocr_failed: 'OCR falhou',
    extracting: 'Extraindo dados',
    indexed: 'Indexado',
    error: 'Erro',
    archived: 'Arquivado',
  }
  return labels[status] ?? status
}

function formatDuration(totalSeconds?: number) {
  if (totalSeconds === undefined || totalSeconds === null) return '-'
  if (totalSeconds < 60) return `${totalSeconds}s`
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes < 60) return `${minutes}min ${seconds}s`
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}h ${remainingMinutes}min`
}

function progressStatusLabel(progress?: DocumentProcessingProgress) {
  if (!progress) return 'Calculando progresso'
  if (progress.status === 'completed') return 'Análise concluída'
  if (progress.status === 'failed') return 'Falha no processamento'
  return progress.active_stage
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [view, setView] = useState<View>('cases')
  const [cases, setCases] = useState<Case[]>([])
  const [selectedCase, setSelectedCase] = useState<Case | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [documentProgress, setDocumentProgress] = useState<Record<string, DocumentProcessingProgress>>({})
  const [analysisSummaries, setAnalysisSummaries] = useState<Record<string, DocumentAnalysisSummary>>({})
  const [documentInventories, setDocumentInventories] = useState<Record<string, DocumentInventory>>({})
  const [ocrSearchResults, setOcrSearchResults] = useState<OCRSearchResult[]>([])
  const [loadingAuth, setLoadingAuth] = useState(true)
  const [loadingCases, setLoadingCases] = useState(false)
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState(false)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [searchingOcr, setSearchingOcr] = useState(false)
  const [submittingCase, setSubmittingCase] = useState(false)
  const [savingCase, setSavingCase] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [creatingFromPdf, setCreatingFromPdf] = useState(false)
  const [deletingCaseId, setDeletingCaseId] = useState<string | null>(null)
  const [runningPericialAnalysisId, setRunningPericialAnalysisId] = useState<string | null>(null)
  const [notice, setNotice] = useState<Notice>(null)
  const [loginForm, setLoginForm] = useState({ email: 'admin@example.com', password: 'admin123' })
  const [caseForm, setCaseForm] = useState(INITIAL_CASE_FORM)
  const [caseEditForm, setCaseEditForm] = useState(INITIAL_CASE_EDIT_FORM)
  const [initialPdfForm, setInitialPdfForm] = useState({
    file: null as File | null,
    category: 'autos_processuais',
    displayName: '',
  })
  const [documentForm, setDocumentForm] = useState({
    file: null as File | null,
    category: 'outro',
    displayName: '',
  })
  const [query, setQuery] = useState('')
  const [ocrQuery, setOcrQuery] = useState('')

  const filteredCases = useMemo(() => {
    const term = query.trim().toLowerCase()
    if (!term) return cases
    return cases.filter((item) =>
      [item.case_number, item.title, item.case_type, item.status, item.court ?? '']
        .join(' ')
        .toLowerCase()
        .includes(term)
    )
  }, [cases, query])

  const loadCases = useCallback(async () => {
    setLoadingCases(true)
    try {
      const data = await casesService.list()
      setCases(data)
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setLoadingCases(false)
    }
  }, [])

  const loadDocumentProgresses = useCallback(async (caseId: string, items: Document[]) => {
    if (items.length === 0) {
      setDocumentProgress({})
      return
    }
    setLoadingProgress(true)
    try {
      const progressItems = await Promise.all(
        items.map((doc) =>
          casesService.getDocumentProgress(caseId, doc.id).catch(() => null)
        )
      )
      setDocumentProgress((prev) => {
        const next: Record<string, DocumentProcessingProgress> = {}
        for (const item of progressItems) {
          if (item) next[item.document_id] = item
        }
        for (const doc of items) {
          if (!next[doc.id] && prev[doc.id]) next[doc.id] = prev[doc.id]
        }
        return next
      })
    } finally {
      setLoadingProgress(false)
    }
  }, [])

  const loadAnalysisSummaries = useCallback(async (caseId: string, items: Document[]) => {
    const completedItems = items.filter((doc) => {
      const progress = documentProgress[doc.id]
      return progress?.status === 'completed'
    })
    if (completedItems.length === 0) return

    setLoadingAnalysis(true)
    try {
      const summaries = await Promise.all(
        completedItems.map((doc) =>
          casesService.getDocumentAnalysisSummary(caseId, doc.id).catch(() => null)
        )
      )
      setAnalysisSummaries((prev) => {
        const next = { ...prev }
        for (const summary of summaries) {
          if (summary) next[summary.document_id] = summary
        }
        return next
      })
    } finally {
      setLoadingAnalysis(false)
    }
  }, [documentProgress])

  const loadDocumentInventories = useCallback(async (caseId: string, items: Document[]) => {
    const completedItems = items.filter((doc) => {
      const progress = documentProgress[doc.id]
      return progress?.status === 'completed'
    })
    if (completedItems.length === 0) return

    const inventories = await Promise.all(
      completedItems.map((doc) =>
        casesService.getDocumentInventory(caseId, doc.id).catch(() => null)
      )
    )
    setDocumentInventories((prev) => {
      const next = { ...prev }
      for (const inventory of inventories) {
        if (inventory) next[inventory.document_id] = inventory
      }
      return next
    })
  }, [documentProgress])

  const loadDocuments = useCallback(async (caseId: string) => {
    setLoadingDocuments(true)
    try {
      const data = await casesService.listDocuments(caseId)
      setDocuments(data)
      await loadDocumentProgresses(caseId, data)
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setLoadingDocuments(false)
    }
  }, [loadDocumentProgresses])

  useEffect(() => {
    if (!selectedCase || documents.length === 0) return
    const hasActiveProcessing = documents.some((doc) => {
      const progress = documentProgress[doc.id]
      return !progress || progress.status === 'processing'
    })
    if (!hasActiveProcessing) return

    const interval = window.setInterval(() => {
      loadDocumentProgresses(selectedCase.id, documents)
    }, 5000)
    return () => window.clearInterval(interval)
  }, [selectedCase, documents, documentProgress, loadDocumentProgresses])

  useEffect(() => {
    if (!selectedCase || documents.length === 0) return
    const hasCompletedWithoutSummary = documents.some((doc) => {
      const progress = documentProgress[doc.id]
      return progress?.status === 'completed' && !analysisSummaries[doc.id]
    })
    if (!hasCompletedWithoutSummary) return
    loadAnalysisSummaries(selectedCase.id, documents)
  }, [selectedCase, documents, documentProgress, analysisSummaries, loadAnalysisSummaries])

  useEffect(() => {
    if (!selectedCase || documents.length === 0) return
    const hasCompletedWithoutInventory = documents.some((doc) => {
      const progress = documentProgress[doc.id]
      return progress?.status === 'completed' && !documentInventories[doc.id]
    })
    if (!hasCompletedWithoutInventory) return
    loadDocumentInventories(selectedCase.id, documents)
  }, [selectedCase, documents, documentProgress, documentInventories, loadDocumentInventories])

  useEffect(() => {
    async function bootstrap() {
      if (!authService.isAuthenticated()) {
        setLoadingAuth(false)
        return
      }
      try {
        const me = await authService.getMe()
        setUser(me)
        await loadCases()
      } catch {
        await authService.logout()
      } finally {
        setLoadingAuth(false)
      }
    }
    bootstrap()
  }, [loadCases])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoadingAuth(true)
    setNotice(null)
    try {
      await authService.login(loginForm.email, loginForm.password)
      const me = await authService.getMe()
      setUser(me)
      await loadCases()
      setView('cases')
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setLoadingAuth(false)
    }
  }

  async function handleLogout() {
    await authService.logout()
    setUser(null)
    setCases([])
    setSelectedCase(null)
    setCaseEditForm(INITIAL_CASE_EDIT_FORM)
    setDocuments([])
    setDocumentProgress({})
    setAnalysisSummaries({})
    setDocumentInventories({})
    setOcrSearchResults([])
    setView('cases')
  }

  async function handleCreateFromPdf(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!initialPdfForm.file) return

    setCreatingFromPdf(true)
    setNotice(null)
    try {
      const result = await casesService.createFromPdf(
        initialPdfForm.file,
        initialPdfForm.category.trim() || 'autos_processuais',
        initialPdfForm.displayName.trim() || undefined
      )
      setInitialPdfForm({ file: null, category: 'autos_processuais', displayName: '' })
      const input = document.getElementById('initial-pdf-file') as HTMLInputElement | null
      if (input) input.value = ''
      await loadCases()
      await openCase(result.case.id)
      const detectedNumber = result.extracted.case_number
        ? ` Número identificado: ${result.extracted.case_number}.`
        : ' Número do processo não encontrado; foi criado um código provisório.'
      setNotice({ tone: 'success', text: `PDF anexado e processo criado.${detectedNumber}` })
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setCreatingFromPdf(false)
    }
  }

  async function handleCreateCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmittingCase(true)
    setNotice(null)
    try {
      const created = await casesService.create({
        case_number: caseForm.case_number.trim(),
        case_type: caseForm.case_type,
        title: caseForm.title.trim(),
        court: caseForm.court.trim() || undefined,
        deadline_date: caseForm.deadline_date || undefined,
        description: caseForm.description.trim() || undefined,
        parties: caseForm.party_name.trim()
          ? [
              {
                name: caseForm.party_name.trim(),
                role: caseForm.party_role.trim() || 'parte',
              },
            ]
          : [],
      })
      setCaseForm(INITIAL_CASE_FORM)
      setNotice({ tone: 'success', text: 'Processo criado com sucesso.' })
      await loadCases()
      await openCase(created.id)
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setSubmittingCase(false)
    }
  }

  async function openCase(caseId: string) {
    setNotice(null)
    try {
      const detail = await casesService.get(caseId)
      setSelectedCase(detail)
      setCaseEditForm({
        case_number: detail.case_number,
        case_type: detail.case_type,
        title: detail.title,
        court: detail.court ?? '',
        deadline_date: detail.deadline_date ?? '',
        description: detail.description ?? '',
        status: detail.status,
      })
      setView('case-detail')
      await loadDocuments(caseId)
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    }
  }

  async function handleUploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedCase || !documentForm.file) return

    setUploading(true)
    setNotice(null)
    try {
      await casesService.uploadDocument(
        selectedCase.id,
        documentForm.file,
        documentForm.category.trim() || 'outro',
        documentForm.displayName.trim() || undefined
      )
      setDocumentForm({ file: null, category: 'outro', displayName: '' })
      const input = document.getElementById('document-file') as HTMLInputElement | null
      if (input) input.value = ''
      setNotice({ tone: 'success', text: 'Documento enviado e registrado.' })
      await loadDocuments(selectedCase.id)
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setUploading(false)
    }
  }

  async function handleUpdateCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedCase) return

    setSavingCase(true)
    setNotice(null)
    try {
      const updated = await casesService.update(selectedCase.id, {
        case_number: caseEditForm.case_number.trim(),
        case_type: caseEditForm.case_type,
        title: caseEditForm.title.trim(),
        court: caseEditForm.court.trim() || undefined,
        deadline_date: caseEditForm.deadline_date || undefined,
        description: caseEditForm.description.trim() || undefined,
        status: caseEditForm.status,
      })
      setSelectedCase(updated)
      setNotice({ tone: 'success', text: 'Dados básicos atualizados.' })
      await loadCases()
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setSavingCase(false)
    }
  }

  async function handleDeleteCase(caseId: string, label: string) {
    const confirmed = window.confirm(
      `Excluir o processo ${label}? Esta ação remove o cadastro do processo e os vínculos salvos no banco.`
    )
    if (!confirmed) return

    setDeletingCaseId(caseId)
    setNotice(null)
    try {
      await casesService.remove(caseId)
      setCases((prev) => prev.filter((item) => item.id !== caseId))
      if (selectedCase?.id === caseId) {
        setSelectedCase(null)
        setDocuments([])
        setDocumentProgress({})
        setAnalysisSummaries({})
        setDocumentInventories({})
        setOcrSearchResults([])
        setCaseEditForm(INITIAL_CASE_EDIT_FORM)
        setView('cases')
      }
      await loadCases()
      setNotice({ tone: 'success', text: 'Processo excluído com sucesso.' })
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setDeletingCaseId(null)
    }
  }

  async function handleOcrSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedCase || !ocrQuery.trim()) return

    setSearchingOcr(true)
    setNotice(null)
    try {
      const results = await casesService.searchOcr(selectedCase.id, ocrQuery.trim())
      setOcrSearchResults(results)
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setSearchingOcr(false)
    }
  }

  async function handleRunPericialAnalysis(documentId: string) {
    if (!selectedCase) return

    setRunningPericialAnalysisId(documentId)
    setNotice(null)
    try {
      const result = await casesService.runPericialAnalysis(selectedCase.id, documentId)
      setDocumentInventories((prev) => ({ ...prev, [documentId]: result.inventory }))
      setNotice({
        tone: 'success',
        text: `Análise pericial concluída: ${result.pages_classified} página(s) classificadas e ${result.inventory.total_groups} item(ns) no inventário.`,
      })
    } catch (error) {
      setNotice({ tone: 'error', text: extractErrorMessage(error) })
    } finally {
      setRunningPericialAnalysisId(null)
    }
  }

  if (loadingAuth && !user) {
    return (
      <main className={styles.centerScreen}>
        <Loader2 className={styles.spin} size={28} />
        <p>Carregando OfficeJoe...</p>
      </main>
    )
  }

  if (!user) {
    return (
      <main className={styles.loginPage}>
        <section className={styles.loginPanel}>
          <p className={styles.eyebrow}>OfficeJoe</p>
          <h1>Entrar no ambiente pericial</h1>
          <form className={styles.formStack} onSubmit={handleLogin}>
            <label>
              Email
              <input
                type="email"
                value={loginForm.email}
                onChange={(event) => setLoginForm((prev) => ({ ...prev, email: event.target.value }))}
                required
              />
            </label>
            <label>
              Senha
              <input
                type="password"
                value={loginForm.password}
                onChange={(event) => setLoginForm((prev) => ({ ...prev, password: event.target.value }))}
                required
              />
            </label>
            {notice && <NoticeBox notice={notice} />}
            <button className={styles.primaryButton} type="submit" disabled={loadingAuth}>
              {loadingAuth ? <Loader2 className={styles.spin} size={18} /> : <CheckCircle2 size={18} />}
              Entrar
            </button>
          </form>
        </section>
      </main>
    )
  }

  return (
    <main className={styles.shell}>
      <aside className={styles.sidebar}>
        <div>
          <p className={styles.eyebrow}>OfficeJoe</p>
          <h1>Perícia evidence-first</h1>
        </div>
        <nav className={styles.nav} aria-label="Navegação principal">
          <button className={view === 'cases' || view === 'case-detail' ? styles.navActive : ''} onClick={() => setView('cases')}>
            Processos
          </button>
          <button className={view === 'dashboard' ? styles.navActive : ''} onClick={() => setView('dashboard')}>
            Dashboard
          </button>
        </nav>
        <div className={styles.userBox}>
          <span>{user.full_name}</span>
          <small>{user.email}</small>
          <button className={styles.ghostButton} onClick={handleLogout}>
            <LogOut size={16} />
            Sair
          </button>
        </div>
      </aside>

      <section className={styles.content}>
        {notice && <NoticeBox notice={notice} />}
        {view === 'dashboard' && <DashboardPage />}
        {view === 'cases' && (
          <CasesView
            cases={filteredCases}
            query={query}
            loadingCases={loadingCases}
            submittingCase={submittingCase}
            creatingFromPdf={creatingFromPdf}
            deletingCaseId={deletingCaseId}
            caseForm={caseForm}
            pdfForm={initialPdfForm}
            onQueryChange={setQuery}
            onRefresh={loadCases}
            onOpenCase={openCase}
            onDeleteCase={handleDeleteCase}
            onCaseFormChange={setCaseForm}
            onCreateCase={handleCreateCase}
            onPdfFormChange={setInitialPdfForm}
            onPdfSubmit={handleCreateFromPdf}
          />
        )}
        {view === 'case-detail' && selectedCase && (
          <CaseDetailView
            currentCase={selectedCase}
            documents={documents}
            documentProgress={documentProgress}
            analysisSummaries={analysisSummaries}
            documentInventories={documentInventories}
            ocrQuery={ocrQuery}
            ocrSearchResults={ocrSearchResults}
            loadingDocuments={loadingDocuments}
            loadingProgress={loadingProgress}
            loadingAnalysis={loadingAnalysis}
            searchingOcr={searchingOcr}
            runningPericialAnalysisId={runningPericialAnalysisId}
            uploading={uploading}
            savingCase={savingCase}
            deletingCaseId={deletingCaseId}
            documentForm={documentForm}
            caseEditForm={caseEditForm}
            onBack={() => setView('cases')}
            onDeleteCase={handleDeleteCase}
            onReloadDocuments={() => loadDocuments(selectedCase.id)}
            onLoadAnalysis={() => loadAnalysisSummaries(selectedCase.id, documents)}
            onRunPericialAnalysis={handleRunPericialAnalysis}
            onOcrQueryChange={setOcrQuery}
            onOcrSearch={handleOcrSearch}
            onDocumentFormChange={setDocumentForm}
            onUploadDocument={handleUploadDocument}
            onCaseEditFormChange={setCaseEditForm}
            onUpdateCase={handleUpdateCase}
          />
        )}
      </section>
    </main>
  )
}

function NoticeBox({ notice }: { notice: Exclude<Notice, null> }) {
  return (
    <div className={`${styles.notice} ${notice.tone === 'error' ? styles.noticeError : styles.noticeSuccess}`}>
      {notice.tone === 'error' ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
      {notice.text}
    </div>
  )
}

function PDFIntakeView({
  form,
  creating,
  onFormChange,
  onSubmit,
}: {
  form: { file: File | null; category: string; displayName: string }
  creating: boolean
  onFormChange: (
    value:
      | { file: File | null; category: string; displayName: string }
      | ((prev: { file: File | null; category: string; displayName: string }) => { file: File | null; category: string; displayName: string })
  ) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <div className={styles.intakeGrid}>
      <section className={`${styles.panel} ${styles.intakePanel}`}>
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Primeiro passo</p>
            <h2>Anexar PDF inicial</h2>
          </div>
          <FileSearch size={22} />
        </div>
        <form className={styles.formStack} onSubmit={onSubmit}>
          <label className={styles.dropZone}>
            <FileUp size={28} />
            <span>{form.file ? form.file.name : 'Selecione o PDF dos autos ou documento principal'}</span>
            <small>O OfficeJoe cria o processo, preserva o original, calcula hash e tenta extrair número, tipo, título e órgão.</small>
            <input
              id="initial-pdf-file"
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) =>
                onFormChange((prev) => ({
                  ...prev,
                  file: event.target.files?.[0] ?? null,
                }))
              }
              required
            />
          </label>
          <div className={styles.formRow}>
            <label>
              Categoria
              <input
                value={form.category}
                onChange={(event) => onFormChange((prev) => ({ ...prev, category: event.target.value }))}
              />
            </label>
            <label>
              Nome de exibição
              <input
                value={form.displayName}
                onChange={(event) => onFormChange((prev) => ({ ...prev, displayName: event.target.value }))}
                placeholder="Opcional"
              />
            </label>
          </div>
          <button className={styles.primaryButton} type="submit" disabled={creating || !form.file}>
            {creating ? <Loader2 className={styles.spin} size={18} /> : <FileSearch size={18} />}
            Criar processo a partir do PDF
          </button>
        </form>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Extração básica</p>
            <h2>O que será preenchido</h2>
          </div>
        </div>
        <div className={styles.stepsList}>
          <div>
            <strong>Identificação</strong>
            <span>Número CNJ do processo, se aparecer nas primeiras páginas.</span>
          </div>
          <div>
            <strong>Classificação</strong>
            <span>Tipo provável: trabalhista, cível, fiscal, extrajudicial ou arbitragem.</span>
          </div>
          <div>
            <strong>Dados mínimos</strong>
            <span>Título, órgão/vara quando detectado, páginas, tamanho e hash SHA-256.</span>
          </div>
          <div>
            <strong>Revisão</strong>
            <span>Após criar, você revisa o processo e pode corrigir os campos.</span>
          </div>
        </div>
      </section>
    </div>
  )
}

function CasesView({
  cases,
  query,
  loadingCases,
  submittingCase,
  creatingFromPdf,
  deletingCaseId,
  caseForm,
  pdfForm,
  onQueryChange,
  onRefresh,
  onOpenCase,
  onDeleteCase,
  onCaseFormChange,
  onCreateCase,
  onPdfFormChange,
  onPdfSubmit,
}: {
  cases: Case[]
  query: string
  loadingCases: boolean
  submittingCase: boolean
  creatingFromPdf: boolean
  deletingCaseId: string | null
  caseForm: typeof INITIAL_CASE_FORM
  pdfForm: { file: File | null; category: string; displayName: string }
  onQueryChange: (value: string) => void
  onRefresh: () => void
  onOpenCase: (caseId: string) => void
  onDeleteCase: (caseId: string, label: string) => void
  onCaseFormChange: (value: typeof INITIAL_CASE_FORM | ((prev: typeof INITIAL_CASE_FORM) => typeof INITIAL_CASE_FORM)) => void
  onCreateCase: (event: FormEvent<HTMLFormElement>) => void
  onPdfFormChange: (
    value:
      | { file: File | null; category: string; displayName: string }
      | ((prev: { file: File | null; category: string; displayName: string }) => { file: File | null; category: string; displayName: string })
  ) => void
  onPdfSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <div className={styles.processesStack}>
      <PDFIntakeView
        form={pdfForm}
        creating={creatingFromPdf}
        onFormChange={onPdfFormChange}
        onSubmit={onPdfSubmit}
      />

      <div className={styles.pageGrid}>
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.eyebrow}>Processos</p>
              <h2>Carteira de perícias</h2>
            </div>
            <button className={styles.iconButton} onClick={onRefresh} aria-label="Atualizar processos">
              <RefreshCw size={18} />
            </button>
          </div>
          <label className={styles.searchBox}>
            <Search size={17} />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Buscar por número, título, status ou vara"
            />
          </label>
          {loadingCases ? (
            <div className={styles.emptyState}>
              <Loader2 className={styles.spin} size={22} />
              Carregando processos...
            </div>
          ) : cases.length === 0 ? (
            <div className={styles.emptyState}>Nenhum processo encontrado.</div>
          ) : (
            <div className={styles.caseList}>
              {cases.map((item) => (
                <article key={item.id} className={styles.caseRow}>
                  <BriefcaseBusiness size={18} />
                  <button className={styles.caseOpenButton} type="button" onClick={() => onOpenCase(item.id)}>
                    <strong>{item.case_number}</strong>
                    <small>{item.title}</small>
                  </button>
                  <div className={styles.rowActions}>
                    <em>{item.status}</em>
                    <button
                      className={styles.dangerIconButton}
                      type="button"
                      onClick={() => onDeleteCase(item.id, item.case_number)}
                      disabled={deletingCaseId === item.id}
                      aria-label={`Excluir processo ${item.case_number}`}
                    >
                      {deletingCaseId === item.id ? <Loader2 className={styles.spin} size={16} /> : <Trash2 size={16} />}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.eyebrow}>Novo registro</p>
              <h2>Criar processo manual</h2>
            </div>
            <Plus size={20} />
          </div>
          <form className={styles.formStack} onSubmit={onCreateCase}>
          <label>
            Número do processo
            <input
              value={caseForm.case_number}
              onChange={(event) => onCaseFormChange((prev) => ({ ...prev, case_number: event.target.value }))}
              placeholder="0000001-00.2025.1.00.0000"
              required
            />
          </label>
          <label>
            Título
            <input
              value={caseForm.title}
              onChange={(event) => onCaseFormChange((prev) => ({ ...prev, title: event.target.value }))}
              placeholder="Perícia trabalhista - verbas rescisórias"
              required
            />
          </label>
          <div className={styles.formRow}>
            <label>
              Tipo
              <select
                value={caseForm.case_type}
                onChange={(event) => onCaseFormChange((prev) => ({ ...prev, case_type: event.target.value as CaseType }))}
              >
                {CASE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Prazo
              <input
                type="date"
                value={caseForm.deadline_date}
                onChange={(event) => onCaseFormChange((prev) => ({ ...prev, deadline_date: event.target.value }))}
              />
            </label>
          </div>
          <label>
            Vara / órgão
            <input
              value={caseForm.court}
              onChange={(event) => onCaseFormChange((prev) => ({ ...prev, court: event.target.value }))}
              placeholder="2ª Vara do Trabalho"
            />
          </label>
          <div className={styles.formRow}>
            <label>
              Parte principal
              <input
                value={caseForm.party_name}
                onChange={(event) => onCaseFormChange((prev) => ({ ...prev, party_name: event.target.value }))}
                placeholder="Nome da parte"
              />
            </label>
            <label>
              Papel
              <input
                value={caseForm.party_role}
                onChange={(event) => onCaseFormChange((prev) => ({ ...prev, party_role: event.target.value }))}
                placeholder="reclamante"
              />
            </label>
          </div>
          <label>
            Descrição
            <textarea
              value={caseForm.description}
              onChange={(event) => onCaseFormChange((prev) => ({ ...prev, description: event.target.value }))}
              rows={4}
              placeholder="Resumo objetivo da perícia"
            />
          </label>
          <button className={styles.primaryButton} type="submit" disabled={submittingCase}>
            {submittingCase ? <Loader2 className={styles.spin} size={18} /> : <Plus size={18} />}
            Criar processo
          </button>
          </form>
        </section>
      </div>
    </div>
  )
}

function CaseDetailView({
  currentCase,
  documents,
  documentProgress,
  analysisSummaries,
  documentInventories,
  ocrQuery,
  ocrSearchResults,
  loadingDocuments,
  loadingProgress,
  loadingAnalysis,
  searchingOcr,
  runningPericialAnalysisId,
  uploading,
  savingCase,
  deletingCaseId,
  documentForm,
  caseEditForm,
  onBack,
  onDeleteCase,
  onReloadDocuments,
  onLoadAnalysis,
  onRunPericialAnalysis,
  onOcrQueryChange,
  onOcrSearch,
  onDocumentFormChange,
  onUploadDocument,
  onCaseEditFormChange,
  onUpdateCase,
}: {
  currentCase: Case
  documents: Document[]
  documentProgress: Record<string, DocumentProcessingProgress>
  analysisSummaries: Record<string, DocumentAnalysisSummary>
  documentInventories: Record<string, DocumentInventory>
  ocrQuery: string
  ocrSearchResults: OCRSearchResult[]
  loadingDocuments: boolean
  loadingProgress: boolean
  loadingAnalysis: boolean
  searchingOcr: boolean
  runningPericialAnalysisId: string | null
  uploading: boolean
  savingCase: boolean
  deletingCaseId: string | null
  documentForm: { file: File | null; category: string; displayName: string }
  caseEditForm: typeof INITIAL_CASE_EDIT_FORM
  onBack: () => void
  onDeleteCase: (caseId: string, label: string) => void
  onReloadDocuments: () => void
  onLoadAnalysis: () => void
  onRunPericialAnalysis: (documentId: string) => void
  onOcrQueryChange: (value: string) => void
  onOcrSearch: (event: FormEvent<HTMLFormElement>) => void
  onDocumentFormChange: (
    value:
      | { file: File | null; category: string; displayName: string }
      | ((prev: { file: File | null; category: string; displayName: string }) => { file: File | null; category: string; displayName: string })
  ) => void
  onUploadDocument: (event: FormEvent<HTMLFormElement>) => void
  onCaseEditFormChange: (
    value:
      | typeof INITIAL_CASE_EDIT_FORM
      | ((prev: typeof INITIAL_CASE_EDIT_FORM) => typeof INITIAL_CASE_EDIT_FORM)
  ) => void
  onUpdateCase: (event: FormEvent<HTMLFormElement>) => void
}) {
  const hasDocuments = documents.length > 0
  const firstDocument = documents[0]
  const firstProgress = firstDocument ? documentProgress[firstDocument.id] : undefined
  const firstSummary = firstDocument ? analysisSummaries[firstDocument.id] : undefined
  const firstInventory = firstDocument ? documentInventories[firstDocument.id] : undefined

  return (
    <div className={styles.detailStack}>
      <section className={`${styles.panel} ${styles.caseHeaderPanel}`}>
        <div className={styles.headerActions}>
          <button className={styles.inlineButton} type="button" onClick={onBack}>
            <ArrowLeft size={16} />
            Voltar para processos
          </button>
          <button
            className={styles.dangerButton}
            type="button"
            onClick={() => onDeleteCase(currentCase.id, currentCase.case_number)}
            disabled={deletingCaseId === currentCase.id}
          >
            {deletingCaseId === currentCase.id ? <Loader2 className={styles.spin} size={16} /> : <Trash2 size={16} />}
            Excluir processo
          </button>
        </div>
        <div className={styles.caseHero}>
          <div>
            <p className={styles.eyebrow}>{currentCase.case_type}</p>
            <h2>{currentCase.title}</h2>
            <p>{currentCase.case_number}</p>
          </div>
          <span className={styles.statusBadge}>{currentCase.status}</span>
        </div>
        <dl className={styles.metaGrid}>
          <div>
            <dt>Prazo</dt>
            <dd>{formatDate(currentCase.deadline_date)}</dd>
          </div>
          <div>
            <dt>Vara / órgão</dt>
            <dd>{currentCase.court || 'Não informado'}</dd>
          </div>
          <div>
            <dt>Partes</dt>
            <dd>{currentCase.parties?.length ? currentCase.parties.map((party) => party.name).join(', ') : 'Sem partes cadastradas'}</dd>
          </div>
        </dl>
      </section>

      <section className={styles.workflowStrip} aria-label="Fluxo do processo">
        <div className={styles.workflowCard}>
          <FileUp size={18} />
          <span>
            <strong>1. PDF recebido</strong>
            <small>{hasDocuments ? `${documents.length} documento(s) anexado(s)` : 'Aguardando documento'}</small>
          </span>
        </div>
        <div className={styles.workflowCard}>
          <ClipboardCheck size={18} />
          <span>
            <strong>2. Dados para revisar</strong>
            <small>Confira número, título, tipo e órgão</small>
          </span>
        </div>
        <div className={styles.workflowCard}>
          <PlayCircle size={18} />
          <span>
            <strong>3. Análise documental</strong>
            <small>Acompanhe OCR, páginas e evidências</small>
          </span>
        </div>
      </section>

      <section className={`${styles.panel} ${styles.documentsPanel}`}>
        <div className={styles.panelHeader}>
          <div>
            <p className={styles.eyebrow}>Documentos</p>
            <h2>PDFs anexados ao processo</h2>
          </div>
          <button className={styles.iconButton} onClick={onReloadDocuments} aria-label="Atualizar documentos">
            <RefreshCw size={18} />
          </button>
        </div>
        {loadingDocuments ? (
          <div className={styles.emptyState}>
            <Loader2 className={styles.spin} size={22} />
            Carregando documentos...
          </div>
        ) : documents.length === 0 ? (
          <div className={styles.emptyState}>Nenhum documento enviado.</div>
        ) : (
          <div className={styles.documentTable}>
            {documents.map((doc) => (
              <article key={doc.id} className={styles.documentRow}>
                <FileText size={20} />
                <div>
                  <strong>{doc.display_name || doc.original_filename}</strong>
                  <small>
                    {doc.category} · {formatBytes(doc.file_size_bytes)}
                    {doc.total_pages ? ` · ${doc.total_pages} pág.` : ''}
                  </small>
                  <code>SHA-256 {doc.sha256_hash.slice(0, 24)}...</code>
                  <DocumentProgressView
                    progress={documentProgress[doc.id]}
                    loading={loadingProgress && !documentProgress[doc.id]}
                  />
                </div>
                <span className={`${styles.statusBadge} ${doc.status === 'error' ? styles.statusError : ''}`}>
                  {documentStatusLabel(doc.status)}
                </span>
              </article>
            ))}
          </div>
        )}
      </section>

      <div className={styles.detailGrid}>
        <div className={styles.detailSide}>
          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <p className={styles.eyebrow}>Análise</p>
                <h2>Análise documental</h2>
              </div>
              <PlayCircle size={20} />
            </div>
            <div className={styles.analysisBox}>
              <div>
                <strong>{hasDocuments ? 'Processamento iniciado automaticamente' : 'Aguardando PDF'}</strong>
                <span>
                  {hasDocuments
                    ? 'Após o upload, o OfficeJoe registra páginas, gera previews e executa OCR básico em fila.'
                    : 'Anexe um PDF para criar o processo e iniciar a fila de processamento.'}
                </span>
              </div>
              <div className={styles.analysisStats}>
                <span>
                  <strong>{documents.length}</strong>
                  documento(s)
                </span>
                <span>
                  <strong>{firstDocument?.total_pages ?? '-'}</strong>
                  páginas no principal
                </span>
                <span>
                  <strong>{firstDocument ? documentStatusLabel(firstDocument.status) : '-'}</strong>
                  status principal
                </span>
                <span>
                  <strong>{firstProgress ? `${firstProgress.progress_percent}%` : '-'}</strong>
                  análise concluída
                </span>
              </div>
              {firstProgress && (
                <DocumentProgressView progress={firstProgress} loading={loadingProgress && firstProgress.status === 'processing'} />
              )}
              {firstProgress?.status === 'completed' ? (
                <AnalysisResultsView
                  summary={firstSummary}
                  inventory={firstInventory}
                  loading={loadingAnalysis}
                  runningPericialAnalysis={runningPericialAnalysisId === firstDocument?.id}
                  query={ocrQuery}
                  results={ocrSearchResults}
                  searching={searchingOcr}
                  onRefresh={onLoadAnalysis}
                  onRunPericialAnalysis={() => firstDocument && onRunPericialAnalysis(firstDocument.id)}
                  onQueryChange={onOcrQueryChange}
                  onSearch={onOcrSearch}
                />
              ) : hasDocuments ? (
                <div className={styles.nextStepBox}>
                  <strong>A análise aparece aqui quando o OCR terminar.</strong>
                  <span>Enquanto isso, acompanhe a barra acima. Quando chegar a 100%, o sistema libera resumo e busca dentro do PDF.</span>
                </div>
              ) : null}
              <button className={styles.primaryButton} type="button" onClick={onReloadDocuments}>
                <RefreshCw size={18} />
                Atualizar análise
              </button>
            </div>
          </section>

          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <p className={styles.eyebrow}>Evidência</p>
                <h2>Enviar outro PDF</h2>
              </div>
              <FileUp size={20} />
            </div>
            <form className={styles.formStack} onSubmit={onUploadDocument}>
              <label>
                Arquivo PDF
                <input
                  id="document-file"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(event) =>
                    onDocumentFormChange((prev) => ({
                      ...prev,
                      file: event.target.files?.[0] ?? null,
                    }))
                  }
                  required
                />
              </label>
              <label>
                Categoria
                <input
                  value={documentForm.category}
                  onChange={(event) => onDocumentFormChange((prev) => ({ ...prev, category: event.target.value }))}
                  placeholder="holerite, contrato, extrato..."
                />
              </label>
              <label>
                Nome de exibição
                <input
                  value={documentForm.displayName}
                  onChange={(event) => onDocumentFormChange((prev) => ({ ...prev, displayName: event.target.value }))}
                  placeholder="Opcional"
                />
              </label>
              <button className={styles.primaryButton} type="submit" disabled={uploading || !documentForm.file}>
                {uploading ? <Loader2 className={styles.spin} size={18} /> : <FileUp size={18} />}
                Enviar documento
              </button>
            </form>
          </section>
        </div>

        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <p className={styles.eyebrow}>Revisão</p>
              <h2>Dados básicos extraídos</h2>
            </div>
            <CheckCircle2 size={20} />
          </div>
          <form className={styles.formStack} onSubmit={onUpdateCase}>
            <label>
              Número do processo
              <input
                value={caseEditForm.case_number}
                onChange={(event) => onCaseEditFormChange((prev) => ({ ...prev, case_number: event.target.value }))}
                required
              />
            </label>
            <label>
              Título
              <input
                value={caseEditForm.title}
                onChange={(event) => onCaseEditFormChange((prev) => ({ ...prev, title: event.target.value }))}
                required
              />
            </label>
            <div className={styles.formRow}>
              <label>
                Tipo
                <select
                  value={caseEditForm.case_type}
                  onChange={(event) => onCaseEditFormChange((prev) => ({ ...prev, case_type: event.target.value as CaseType }))}
                >
                  {CASE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Status
                <input
                  value={caseEditForm.status}
                  onChange={(event) => onCaseEditFormChange((prev) => ({ ...prev, status: event.target.value as Case['status'] }))}
                />
              </label>
            </div>
            <label>
              Prazo
              <input
                type="date"
                value={caseEditForm.deadline_date}
                onChange={(event) => onCaseEditFormChange((prev) => ({ ...prev, deadline_date: event.target.value }))}
              />
            </label>
            <label>
              Vara / órgão
              <input
                value={caseEditForm.court}
                onChange={(event) => onCaseEditFormChange((prev) => ({ ...prev, court: event.target.value }))}
              />
            </label>
            <label>
              Descrição
              <textarea
                rows={5}
                value={caseEditForm.description}
                onChange={(event) => onCaseEditFormChange((prev) => ({ ...prev, description: event.target.value }))}
              />
            </label>
            <button className={styles.primaryButton} type="submit" disabled={savingCase}>
              {savingCase ? <Loader2 className={styles.spin} size={18} /> : <CheckCircle2 size={18} />}
              Salvar dados revisados
            </button>
          </form>
        </section>
      </div>

      <section className={styles.panel}>
        <CaseOperationsPanel caseId={currentCase.id} documents={documents} />
      </section>
    </div>
  )
}

function DocumentProgressView({
  progress,
  loading,
}: {
  progress?: DocumentProcessingProgress
  loading: boolean
}) {
  const percent = progress?.progress_percent ?? 0
  const safePercent = Math.max(0, Math.min(percent, 100))
  return (
    <div className={styles.progressBlock}>
      <div className={styles.progressHeader}>
        <span>{progressStatusLabel(progress)}</span>
        <strong>{loading && !progress ? '...' : `${safePercent}%`}</strong>
      </div>
      <div className={styles.progressTrack} aria-label="Progresso de processamento">
        <span
          className={`${styles.progressFill} ${progress?.status === 'failed' ? styles.progressFailed : ''}`}
          style={{ width: `${safePercent}%` }}
        />
      </div>
      {progress ? (
        <div className={styles.progressMeta}>
          <span>
            OCR {progress.ocr_completed}/{progress.pages_total || 0} pág.
          </span>
          <span>Decorrido {formatDuration(progress.elapsed_seconds)}</span>
          <span>
            Restante {progress.status === 'completed' ? '0s' : formatDuration(progress.estimated_remaining_seconds)}
          </span>
        </div>
      ) : (
        <div className={styles.progressMeta}>
          <span>{loading ? 'Consultando processamento...' : 'Progresso ainda indisponível'}</span>
        </div>
      )}
    </div>
  )
}

function AnalysisResultsView({
  summary,
  inventory,
  loading,
  runningPericialAnalysis,
  query,
  results,
  searching,
  onRefresh,
  onRunPericialAnalysis,
  onQueryChange,
  onSearch,
}: {
  summary?: DocumentAnalysisSummary
  inventory?: DocumentInventory
  loading: boolean
  runningPericialAnalysis: boolean
  query: string
  results: OCRSearchResult[]
  searching: boolean
  onRefresh: () => void
  onRunPericialAnalysis: () => void
  onQueryChange: (value: string) => void
  onSearch: (event: FormEvent<HTMLFormElement>) => void
}) {
  if (loading && !summary) {
    return (
      <div className={styles.nextStepBox}>
        <Loader2 className={styles.spin} size={18} />
        <span>Montando resumo do texto extraído...</span>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className={styles.nextStepBox}>
        <strong>Análise concluída. Resumo ainda não carregado.</strong>
        <span>Atualize os resultados para buscar o texto extraído e exibir os primeiros trechos encontrados.</span>
        <button className={styles.inlineButton} type="button" onClick={onRefresh}>
          <RefreshCw size={16} />
          Atualizar resultados
        </button>
      </div>
    )
  }

  return (
    <div className={styles.resultsBox}>
      <div className={styles.resultHeader}>
        <div>
          <strong>Resultados da análise</strong>
          <span>
            {summary.status === 'ready'
              ? `${formatNumber(summary.pages_with_text)} de ${formatNumber(summary.pages_total)} página(s) com texto extraído`
              : 'OCR concluído, mas nenhum texto foi extraído deste documento.'}
          </span>
        </div>
        <button className={styles.iconButton} type="button" onClick={onRefresh} aria-label="Atualizar resultados da análise">
          <RefreshCw size={18} />
        </button>
      </div>

      <div className={styles.resultStats}>
        <span>
          <strong>{formatNumber(summary.text_blocks)}</strong>
          blocos de texto
        </span>
        <span>
          <strong>{formatNumber(summary.extracted_text_chars)}</strong>
          caracteres lidos
        </span>
      </div>

      {summary.top_terms.length > 0 && (
        <div className={styles.termCloud}>
          {summary.top_terms.map((term) => (
            <span key={term.term}>
              {term.term} <small>{term.count}</small>
            </span>
          ))}
        </div>
      )}

      {summary.snippets.length > 0 && (
        <div className={styles.snippetList}>
          {summary.snippets.map((snippet) => (
            <article key={snippet.page_number}>
              <strong>Página {snippet.page_number}</strong>
              <p>{snippet.text}</p>
            </article>
          ))}
        </div>
      )}

      <div className={styles.pericialStage}>
        <div className={styles.resultHeader}>
          <div>
            <strong>Análise pericial</strong>
            <span>
              {inventory?.total_groups
                ? `${inventory.total_groups} item(ns) no inventário documental.`
                : 'Classifique as páginas e gere o inventário dos autos.'}
            </span>
          </div>
          <button
            className={styles.primaryButton}
            type="button"
            onClick={onRunPericialAnalysis}
            disabled={runningPericialAnalysis || summary.status !== 'ready'}
          >
            {runningPericialAnalysis ? <Loader2 className={styles.spin} size={18} /> : <ClipboardCheck size={18} />}
            Executar análise pericial
          </button>
        </div>

        {inventory && inventory.items.length > 0 && (
          <div className={styles.inventoryList}>
            {inventory.items.slice(0, 8).map((item) => (
              <article key={item.id}>
                <strong>{item.custom_label || item.document_class}</strong>
                <span>
                  Págs. {item.start_page}-{item.end_page} · {item.page_count} página(s)
                  {typeof item.confidence_avg === 'number'
                    ? ` · ${Math.round(item.confidence_avg * 100)}% confiança`
                    : ''}
                </span>
              </article>
            ))}
          </div>
        )}
      </div>

      <form className={styles.ocrSearchForm} onSubmit={onSearch}>
        <label className={styles.searchBox}>
          <Search size={17} />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Buscar no texto do PDF"
          />
        </label>
        <button className={styles.primaryButton} type="submit" disabled={searching || !query.trim()}>
          {searching ? <Loader2 className={styles.spin} size={18} /> : <Search size={18} />}
          Buscar
        </button>
      </form>

      {results.length > 0 && (
        <div className={styles.searchResults}>
          {results.map((result) => (
            <article key={`${result.file_page_id}-${result.page_number}-${result.snippet}`}>
              <strong>Página {result.page_number}</strong>
              <p>{result.snippet}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
