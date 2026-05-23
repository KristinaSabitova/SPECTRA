import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft, Share2, AlertTriangle, Clock,
  Activity, Database, GitBranch, ShieldAlert, CheckCircle2,
} from 'lucide-react'
import { useRun } from '@/hooks/useRun'
import { auditsApi } from '@/services/api'
import EcosystemGraph from '@/components/graph/EcosystemGraph'
import EventTimeline from '@/components/audit/EventTimeline'
import RiskScoring from '@/components/audit/RiskScoring'
import FindingsList from '@/components/audit/FindingsList'
import ReportExport from '@/components/report/ReportExport'
import Badge from '@/components/common/Badge'
import Spinner from '@/components/common/Spinner'
import Alert from '@/components/common/Alert'
import type { Audit, RunStatus, Severity, PersistenceDetail } from '@/types'

const STATUS_VARIANT: Record<RunStatus, string> = {
  queued:    'pending',
  running:   'running',
  completed: 'completed',
  failed:    'failed',
  cancelled: 'failed',
}

function StatCard({ icon: Icon, label, value, sub }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string
}) {
  return (
    <div className="stat-card">
      <div className="stat-card-icon"><Icon size={16} /></div>
      <div className="stat-card-body">
        <p className="stat-card-label">{label}</p>
        <p className="stat-card-value">{value}</p>
        {sub && <p className="stat-card-sub">{sub}</p>}
      </div>
    </div>
  )
}

// ── Persistence panel ─────────────────────────────────────────────────

function PersistencePanel({ detail, detected }: { detail: PersistenceDetail | null; detected: boolean }) {
  const { t } = useTranslation()

  if (!detected && !detail) {
    return (
      <div className="persist-panel persist-panel--clean">
        <CheckCircle2 size={20} className="persist-icon persist-icon--ok" />
        <p className="persist-label">{t('run.notDetected')}</p>
      </div>
    )
  }

  return (
    <div className="persist-panel persist-panel--alert">
      <div className="persist-header">
        <ShieldAlert size={16} className="persist-icon persist-icon--danger" />
        <span className="persist-title">{t('run.detected')}</span>
        {detail && (
          <span className="persist-deviation">
            {t('graph.depth')} ×{detail.probes_run ?? 0} — max {((detail.max_deviation ?? 0) * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {detail?.indicators && detail.indicators.length > 0 && (
        <ul className="persist-indicators">
          {detail.indicators.map((ind, i) => (
            <li key={i} className="persist-indicator">{ind}</li>
          ))}
        </ul>
      )}

      {detail?.deviation_by_probe && (
        <div className="persist-probes">
          {Object.entries(detail.deviation_by_probe).map(([probe, val]) => (
            <div key={probe} className="persist-probe-row">
              <span className="persist-probe-name">{probe.replace(/_/g, ' ')}</span>
              <div className="persist-probe-bar-track">
                <div
                  className="persist-probe-bar-fill"
                  style={{ width: `${(val * 100).toFixed(0)}%` }}
                />
              </div>
              <span className="persist-probe-val">{(val * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tabs ──────────────────────────────────────────────────────────────

type Tab = 'overview' | 'timeline' | 'findings'

export default function RunDetail() {
  const { id = '' } = useParams<{ id: string }>()
  const { t }       = useTranslation()
  const { run, events, riskScore, loading, error } = useRun(id)
  const [audit, setAudit]           = useState<Audit | null>(null)
  const [tab, setTab]               = useState<Tab>('overview')
  const [showReport, setShowReport] = useState(false)

  useEffect(() => {
    if (!id) return
    auditsApi.get(id).then(r => setAudit(r.data)).catch(() => {})
  }, [id])

  if (loading) return <Spinner page />
  if (error)   return <Alert type="error" message={error} />
  if (!run)    return <Alert type="error" message={t('common.error')} />

  const isLive  = run.status === 'queued' || run.status === 'running'
  const elapsed = run.started_at && run.completed_at
    ? Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000)
    : null

  const findingEvents = events.filter(e => e.event_type === 'finding_generated')
  const displayName   = audit?.name ?? trimUrl(run.target_url)

  return (
    <div className="run-detail">
      {/* Header */}
      <div className="run-header">
        <div className="run-header-top">
          <Link to="/audits" className="run-back-link">
            <ArrowLeft size={14} />
            {t('common.back')}
          </Link>

          <div className="run-header-actions">
            {run.status === 'completed' && (
              <button className="btn btn--secondary btn--sm" onClick={() => setShowReport(true)}>
                <Share2 size={13} />
                {t('report.export')}
              </button>
            )}
          </div>
        </div>

        <div className="run-header-main">
          <div className="run-header-info">
            <h1 className="run-target" title={run.target_url}>
              {displayName}
            </h1>
            <div className="run-header-meta">
              {audit?.pipeline_name && (
                <span className="run-pipeline-badge">
                  <GitBranch size={11} />
                  {audit.pipeline_name}
                </span>
              )}
              {run.framework && !audit?.pipeline_name && (
                <span className="run-framework-badge">
                  <GitBranch size={11} />
                  {run.framework}
                </span>
              )}
              <Badge
                variant={(STATUS_VARIANT[run.status] as Severity)}
                label={t(`audits.status.${run.status}`)}
              />
              {isLive && <span className="live-indicator"><span className="live-dot" />{t('run.liveIndicator')}</span>}
            </div>
          </div>

          {riskScore && (
            <div className="run-risk-badge" style={{ '--risk-color': riskLevelColor(riskScore.level) } as React.CSSProperties}>
              <span className="run-risk-score">{riskScore.composite}</span>
              <span className="run-risk-label">{t(`risk.levels.${riskScore.level}`)}</span>
            </div>
          )}
        </div>

        {/* Stat row */}
        <div className="run-stats-row">
          <StatCard icon={Activity}      label={t('run.events')}   value={run.total_events} />
          <StatCard icon={AlertTriangle} label={t('run.findings')} value={run.findings_count} />
          <StatCard
            icon={Database}
            label={t('run.blastScore')}
            value={run.blast_radius_score != null ? `${run.blast_radius_score.toFixed(1)}/100` : '—'}
          />
          <StatCard
            icon={Clock}
            label={t('run.duration')}
            value={elapsed != null ? `${elapsed}s` : '—'}
            sub={run.started_at ? new Date(run.started_at).toLocaleString() : undefined}
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="run-tabs">
        {([
          { id: 'overview' as Tab,  label: t('graph.title'),    count: undefined },
          { id: 'timeline' as Tab,  label: t('timeline.title'), count: events.length },
          { id: 'findings' as Tab,  label: t('findings.title'), count: findingEvents.length },
        ]).map(({ id, label, count }) => (
          <button
            key={id}
            className={`run-tab${tab === id ? ' run-tab--active' : ''}`}
            onClick={() => setTab(id)}
          >
            {label}
            {count !== undefined && ` (${count})`}
          </button>
        ))}
      </div>

      {/* Overview: graph + risk + persistence */}
      {tab === 'overview' && (
        <div className="run-overview-grid">
          <div className="run-graph-col">
            <div className="section-card">
              <h3 className="section-card-title">{t('graph.title')}</h3>
              <EcosystemGraph detail={run.blast_radius_detail} />
            </div>
          </div>
          <div className="run-risk-col">
            <div className="section-card">
              <h3 className="section-card-title">{t('risk.title')}</h3>
              <RiskScoring score={riskScore} />
            </div>
            <div className="section-card" style={{ marginTop: 16 }}>
              <h3 className="section-card-title">{t('run.persistence')}</h3>
              <PersistencePanel
                detail={run.persistence_detail}
                detected={run.persistence_detected}
              />
            </div>
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <div className="section-card">
          <h3 className="section-card-title">{t('timeline.title')}</h3>
          <EventTimeline events={events} isLive={isLive} />
        </div>
      )}

      {tab === 'findings' && (
        <div className="section-card">
          <h3 className="section-card-title">{t('findings.title')}</h3>
          <FindingsList events={events} />
        </div>
      )}

      {showReport && (
        <ReportExport
          run={run}
          events={events}
          onClose={() => setShowReport(false)}
        />
      )}
    </div>
  )
}

function trimUrl(url: string): string {
  try {
    const u = new URL(url)
    return u.host + u.pathname.replace(/\/$/, '')
  } catch { return url }
}

function riskLevelColor(level: string): string {
  const map: Record<string, string> = {
    low: '#22C55E', medium: '#EAB308', high: '#F97316',
    critical: '#EF4444', maximum: '#991B1B',
  }
  return map[level] ?? '#64748B'
}
