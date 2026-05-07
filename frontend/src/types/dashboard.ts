import type { LucideIcon } from 'lucide-react'

export type DashboardMetricKey =
  | 'activeCases'
  | 'criticalDeadlines'
  | 'openDiligences'
  | 'pendingDocuments'
  | 'processingFiles'
  | 'criticalLimitations'

export type DashboardTrend = 'up' | 'down' | 'flat'

export interface DashboardMetric {
  key: DashboardMetricKey
  label: string
  value: number
  detail: string
  tone: 'work' | 'warning' | 'attention' | 'info' | 'processing' | 'critical'
  trend: DashboardTrend
  trendLabel: string
}

export type DashboardAlertSeverity = 'crítica' | 'alta' | 'média'

export interface DashboardAlert {
  id: string
  caseNumber: string
  subject: string
  category: string
  dueLabel: string
  severity: DashboardAlertSeverity
  owner: string
}

export interface DashboardSummary {
  generatedAt: string
  metrics: DashboardMetric[]
  alerts: DashboardAlert[]
}

export interface DashboardStatCardProps {
  metric: DashboardMetric
  icon: LucideIcon
}

export interface DashboardAlertTableProps {
  alerts: DashboardAlert[]
}
