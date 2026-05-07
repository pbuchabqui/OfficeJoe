import {
  AlertOctagon,
  BriefcaseBusiness,
  Clock3,
  FileCheck2,
  FileClock,
  Inbox,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { mockDashboardData } from './mockDashboardData'
import { DashboardAlertTable } from './DashboardAlertTable'
import { DashboardStatCard } from './DashboardStatCard'
import type { DashboardMetricKey } from '../../types/dashboard'
import styles from './Dashboard.module.css'

const metricIcons = {
  activeCases: BriefcaseBusiness,
  criticalDeadlines: Clock3,
  openDiligences: Inbox,
  pendingDocuments: FileCheck2,
  processingFiles: FileClock,
  criticalLimitations: AlertOctagon,
} satisfies Record<DashboardMetricKey, LucideIcon>

export function DashboardPage() {
  const generatedAt = new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(mockDashboardData.generatedAt))

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>OfficeJoe</p>
          <h1>Dashboard da perícia</h1>
        </div>
        <p className={styles.timestamp}>Atualizado em {generatedAt}</p>
      </header>

      <section className={styles.statsGrid} aria-label="Resumo operacional">
        {mockDashboardData.metrics.map((metric) => (
          <DashboardStatCard
            key={metric.key}
            metric={metric}
            icon={metricIcons[metric.key]}
          />
        ))}
      </section>

      <DashboardAlertTable alerts={mockDashboardData.alerts} />
    </main>
  )
}

export default DashboardPage
