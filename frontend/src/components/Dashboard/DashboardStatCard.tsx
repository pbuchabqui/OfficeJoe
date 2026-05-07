import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { DashboardStatCardProps, DashboardTrend } from '../../types/dashboard'
import styles from './Dashboard.module.css'

const trendIcons = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: ArrowRight,
} satisfies Record<DashboardTrend, LucideIcon>

export function DashboardStatCard({ metric, icon: Icon }: DashboardStatCardProps) {
  const TrendIcon = trendIcons[metric.trend]

  return (
    <article className={`${styles.statCard} ${styles[metric.tone]}`}>
      <div className={styles.statHeader}>
        <span className={styles.statIcon} aria-hidden="true">
          <Icon size={20} />
        </span>
        <span className={styles.trend}>
          <TrendIcon size={14} />
          {metric.trendLabel}
        </span>
      </div>
      <div>
        <p className={styles.statLabel}>{metric.label}</p>
        <strong className={styles.statValue}>{metric.value}</strong>
        <p className={styles.statDetail}>{metric.detail}</p>
      </div>
    </article>
  )
}
