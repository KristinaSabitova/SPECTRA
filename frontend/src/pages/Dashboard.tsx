import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { GitBranch, ShieldCheck, AlertTriangle, FileText } from 'lucide-react'
import { useDataStore } from '@/store/data'
import Badge from '@/components/common/Badge'
import Spinner from '@/components/common/Spinner'
import type { AuditStatus } from '@/types'

const STATUS_VARIANT: Record<AuditStatus, string> = {
  pending:   'queued',
  running:   'running',
  completed: 'completed',
  failed:    'failed',
}

interface StatCardProps {
  icon: React.ReactNode
  iconClass: string
  value: number
  label: string
  desc: string
}

function StatCard({ icon, iconClass, value, label, desc }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className={`stat-card-icon ${iconClass}`}>{icon}</div>
      <div className="stat-card-value">{value}</div>
      <div className="stat-card-label">{label}</div>
      <div className="stat-card-desc">{desc}</div>
    </div>
  )
}

export default function Dashboard() {
  const { t }     = useTranslation()
  const pipelines = useDataStore(s => s.pipelines)
  const audits    = useDataStore(s => s.audits)
  const reports   = useDataStore(s => s.reports)
  const loading   = useDataStore(s => s.loading)
  const loaded    = useDataStore(s => s.loaded)

  const findings = audits.reduce((sum, a) => sum + a.findings_count, 0)
  const recent   = audits.slice(0, 6)

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{t('dashboard.title')}</h1>
          <p className="page-subtitle">{t('dashboard.overview')}</p>
        </div>
      </div>

      {!loaded && loading && <Spinner page />}

      {loaded && (
        <>
          <div className="stats-grid section">
            <StatCard icon={<GitBranch />}     iconClass="blue"  value={pipelines.length} label={t('dashboard.stats.pipelines')} desc={t('dashboard.stats.pipelinesDesc')} />
            <StatCard icon={<ShieldCheck />}   iconClass="green" value={audits.length}    label={t('dashboard.stats.audits')}    desc={t('dashboard.stats.auditsDesc')} />
            <StatCard icon={<AlertTriangle />} iconClass="red"   value={findings}         label={t('dashboard.stats.findings')}  desc={t('dashboard.stats.findingsDesc')} />
            <StatCard icon={<FileText />}      iconClass="amber" value={reports.length}   label={t('dashboard.stats.reports')}   desc={t('dashboard.stats.reportsDesc')} />
          </div>

          <div className="section">
            <h2 className="section-title">{t('dashboard.recentActivity')}</h2>

            {recent.length === 0 ? (
              <div className="card">
                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t('dashboard.noActivity')}</p>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t('audits.columns.name')}</th>
                      <th>{t('audits.columns.pipeline')}</th>
                      <th>{t('audits.columns.status')}</th>
                      <th>{t('audits.columns.findings')}</th>
                      <th>{t('audits.columns.created')}</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map(audit => (
                      <tr key={audit.id}>
                        <td style={{ fontWeight: 500 }}>
                          {audit.name ?? <span style={{ color: 'var(--text-muted)' }}>—</span>}
                        </td>
                        <td style={{ color: 'var(--text-secondary)' }}>{audit.pipeline_name}</td>
                        <td>
                          <Badge
                            variant={STATUS_VARIANT[audit.status] as 'queued' | 'running' | 'completed' | 'failed'}
                            label={t(`audits.status.${audit.status}`)}
                          />
                        </td>
                        <td style={{ fontWeight: 600 }}>{audit.findings_count}</td>
                        <td className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                          {new Date(audit.created_at).toLocaleDateString()}
                        </td>
                        <td>
                          <Link to={`/audits/${audit.id}`} className="btn btn-ghost btn-sm">
                            {t('common.view')}
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
