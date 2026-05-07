import { AlertTriangle } from 'lucide-react'
import type {
  DashboardAlertSeverity,
  DashboardAlertTableProps,
} from '../../types/dashboard'
import styles from './Dashboard.module.css'

const severityClass = {
  crítica: styles.severityCritical,
  alta: styles.severityHigh,
  média: styles.severityMedium,
} satisfies Record<DashboardAlertSeverity, string>

export function DashboardAlertTable({ alerts }: DashboardAlertTableProps) {
  return (
    <section className={styles.alertPanel} aria-labelledby="dashboard-alerts-title">
      <div className={styles.panelHeader}>
        <div>
          <p className={styles.eyebrow}>Alertas</p>
          <h2 id="dashboard-alerts-title">Prioridades operacionais</h2>
        </div>
        <span className={styles.alertCount}>
          <AlertTriangle size={16} />
          {alerts.length}
        </span>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.alertTable}>
          <thead>
            <tr>
              <th>Processo</th>
              <th>Assunto</th>
              <th>Categoria</th>
              <th>Prazo</th>
              <th>Severidade</th>
              <th>Responsável</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert) => (
              <tr key={alert.id}>
                <td className={styles.caseNumber}>{alert.caseNumber}</td>
                <td>{alert.subject}</td>
                <td>{alert.category}</td>
                <td>{alert.dueLabel}</td>
                <td>
                  <span className={`${styles.severity} ${severityClass[alert.severity]}`}>
                    {alert.severity}
                  </span>
                </td>
                <td>{alert.owner}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
