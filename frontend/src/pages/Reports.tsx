import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { FileText, Eye, Download } from 'lucide-react'
import { reportsApi, engineApi } from '@/services/api'
import ReportExport from '@/components/report/ReportExport'
import Badge from '@/components/common/Badge'
import Button from '@/components/common/Button'
import Spinner from '@/components/common/Spinner'
import EmptyState from '@/components/common/EmptyState'
import type { ReportListItem, RunResponse, EngineEvent, Severity } from '@/types'

function riskLevel(item: ReportListItem): { level: string; variant: Severity } {
  const score = item.blast_radius_score ?? 0
  if (item.persistence_detected || score >= 70) return { level: 'critical', variant: 'critical' }
  if (score >= 50) return { level: 'high',     variant: 'high' }
  if (score >= 30) return { level: 'medium',   variant: 'medium' }
  return             { level: 'low',      variant: 'low' }
}

export default function Reports() {
  const { t } = useTranslation()
  const [reports, setReports]           = useState<ReportListItem[]>([])
  const [loading, setLoading]           = useState(true)
  const [viewRun, setViewRun]           = useState<{ run: RunResponse; events: EngineEvent[] } | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    reportsApi.list()
      .then(r => setReports(r.data))
      .catch(() => setReports([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  async function handleView(id: string) {
    setLoadingReport(true)
    try {
      const [runRes, eventsRes] = await Promise.all([
        engineApi.getRun(id),
        engineApi.getEvents(id),
      ])
      setViewRun({ run: runRes.data, events: eventsRes.data })
    } catch {
      /* ignore */
    } finally {
      setLoadingReport(false)
    }
  }

  function handleDownload(id: string, name: string | null) {
    engineApi.getRun(id).then(async runRes => {
      const eventsRes = await engineApi.getEvents(id)
      const data = {
        report_id: id,
        audit_name: name,
        run: runRes.data,
        events_count: eventsRes.data.length,
        generated_at: new Date().toISOString(),
      }
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `spectra-report-${id.slice(0, 8)}.json`
      a.click()
      URL.revokeObjectURL(url)
    }).catch(() => {})
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{t('reports.title')}</h1>
          <p className="page-subtitle">{t('reports.subtitle')}</p>
        </div>
      </div>

      {loading && <Spinner page />}

      {!loading && reports.length === 0 && (
        <EmptyState
          icon={FileText}
          title={t('reports.empty')}
          description={t('reports.emptyDesc')}
        />
      )}

      {!loading && reports.length > 0 && (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>{t('reports.columns.audit')}</th>
                <th>{t('audits.columns.pipeline')}</th>
                <th>{t('reports.columns.findings')}</th>
                <th>{t('reports.columns.maxSeverity')}</th>
                <th>{t('reports.columns.generated')}</th>
                <th>{t('reports.columns.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {reports.map(item => {
                const { level, variant } = riskLevel(item)
                return (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 500 }}>
                      {item.audit_name ?? <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.id.slice(0, 8)}…</span>}
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>{item.pipeline_name}</td>
                    <td style={{ fontWeight: 600 }}>{item.findings_count}</td>
                    <td>
                      <Badge variant={variant} label={t(`risk.levels.${level}`)} />
                    </td>
                    <td className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {new Date(item.generated_at).toLocaleString()}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={loadingReport}
                          onClick={() => handleView(item.id)}
                        >
                          <Eye size={13} />
                          {t('common.view')}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownload(item.id, item.audit_name)}
                        >
                          <Download size={13} />
                          {t('reports.download')}
                        </Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {loadingReport && (
        <div className="modal-overlay">
          <Spinner page />
        </div>
      )}

      {viewRun && (
        <ReportExport
          run={viewRun.run}
          events={viewRun.events}
          onClose={() => setViewRun(null)}
        />
      )}
    </div>
  )
}
