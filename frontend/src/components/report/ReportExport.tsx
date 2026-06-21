import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Printer, Download, FileText, Code } from 'lucide-react'
import Button from '@/components/common/Button'
import type { RunResponse, EngineEvent, RiskScore } from '@/types'
import { calculateRiskScore } from '@/hooks/useRun'

type Level = 'executive' | 'technical' | 'raw'

// ── Executive report ──────────────────────────────────────────────────

function ExecutiveReport({ run, score }: { run: RunResponse; score: RiskScore }) {
  const { t } = useTranslation()
  const date = new Date(run.created_at).toLocaleDateString()

  return (
    <div className="rpt rpt--executive">
      <header className="rpt-header">
        <div className="rpt-logo">SPECTRA</div>
        <div className="rpt-meta">
          <span>{t('report.confidential')}</span>
          <span>{date}</span>
        </div>
      </header>

      <h1 className="rpt-title">{t('report.sections.summary')}</h1>

      <div className="rpt-score-block">
        <div className="rpt-score-number" style={{ color: levelColor(score.level) }}>
          {score.composite}<span>/100</span>
        </div>
        <div className="rpt-score-level">{t(`risk.levels.${score.level}`).toUpperCase()}</div>
      </div>

      <section className="rpt-section">
        <h2>{t('report.sections.target')}</h2>
        <table className="rpt-info-table">
          <tbody>
            <tr><td>{t('run.target')}</td><td><code>{run.target_url}</code></td></tr>
            <tr><td>{t('run.framework')}</td><td>{run.framework ?? t('audits.noFramework')}</td></tr>
            <tr><td>{t('run.blastScore')}</td><td>{run.blast_radius_score?.toFixed(1) ?? '—'}/100</td></tr>
            <tr><td>{t('run.persistence')}</td><td>{run.persistence_detected ? t('run.detected') : t('run.notDetected')}</td></tr>
            <tr><td>{t('run.findings')}</td><td>{run.findings_count}</td></tr>
          </tbody>
        </table>
      </section>

      <section className="rpt-section">
        <h2>{t('report.sections.riskScore')}</h2>
        <div className="rpt-score-breakdown">
          {[
            { key: 'blast',       val: score.blast,       w: 40 },
            { key: 'persistence', val: score.persistence, w: 30 },
            { key: 'surface',     val: score.surface,     w: 15 },
            { key: 'findings',    val: score.findings,    w: 15 },
          ].map(({ key, val, w }) => (
            <div key={key} className="rpt-score-row">
              <span>{t(`risk.components.${key}`)}</span>
              <div className="rpt-bar-outer">
                <div className="rpt-bar-inner" style={{ width: `${val}%` }} />
              </div>
              <span className="rpt-score-val">{Math.round(val)} <span className="rpt-weight">({w}%)</span></span>
            </div>
          ))}
        </div>
      </section>

      <section className="rpt-section">
        <h2>{t('report.sections.recommendations')}</h2>
        <ol className="rpt-recommendations">
          {score.blast > 60 && <li>Reduce pipeline blast radius by isolating high-criticality tools behind authorization boundaries.</li>}
          {run.persistence_detected && <li>Investigate and eliminate instruction persistence vectors. Review memory/RAG layers for injected content.</li>}
          {score.findings > 40 && <li>Audit all indirect input channels (retrieved documents, tool outputs) for untrusted content before LLM processing.</li>}
          {score.surface > 50 && <li>Minimize the attack surface by restricting exposed endpoints and removing unused tools.</li>}
          <li>Implement output filtering and response classification at the pipeline boundary.</li>
          <li>Establish regular red-team assessments using SPECTRA on all production AI pipelines.</li>
        </ol>
      </section>

      <footer className="rpt-footer">
        {t('report.generatedBy')} · {date}
      </footer>
    </div>
  )
}

// ── Technical report ──────────────────────────────────────────────────

function TechnicalReport({ run, events }: { run: RunResponse; events: EngineEvent[] }) {
  const { t } = useTranslation()
  const findings = events.filter(e => e.event_type === 'finding_generated')
  const blast = run.blast_radius_detail
  const persistence = run.persistence_detail

  return (
    <div className="rpt rpt--technical">
      <header className="rpt-header">
        <div className="rpt-logo">SPECTRA</div>
        <div className="rpt-meta"><span>{t('report.confidential')}</span></div>
      </header>

      <h1 className="rpt-title">Technical Security Assessment</h1>

      <section className="rpt-section">
        <h2>{t('report.sections.target')}</h2>
        <table className="rpt-info-table">
          <tbody>
            <tr><td>Target URL</td><td><code>{run.target_url}</code></td></tr>
            <tr><td>Framework</td><td>{run.framework ?? 'Unknown'}</td></tr>
            <tr><td>Run ID</td><td><code>{run.id}</code></td></tr>
            <tr><td>Status</td><td>{run.status}</td></tr>
            <tr><td>Total Events</td><td>{run.total_events}</td></tr>
            <tr><td>Started</td><td>{run.started_at ? new Date(run.started_at).toLocaleString() : '—'}</td></tr>
            <tr><td>Completed</td><td>{run.completed_at ? new Date(run.completed_at).toLocaleString() : '—'}</td></tr>
          </tbody>
        </table>
      </section>

      <section className="rpt-section">
        <h2>{t('report.sections.blastRadius')}</h2>
        {blast ? (
          <>
            <p><strong>Score:</strong> {blast.score}/100 · <strong>Affected nodes:</strong> {blast.affected_nodes.length} · <strong>Cascade depth:</strong> {blast.cascade_depth}</p>
            <table className="rpt-info-table">
              <thead><tr><th>Node</th><th>Type</th><th>Criticality</th><th>Depth</th></tr></thead>
              <tbody>
                {blast.node_details.map(n => (
                  <tr key={n.id}>
                    <td><code>{n.label}</code></td>
                    <td>{n.type}</td>
                    <td>{(n.criticality * 100).toFixed(0)}%</td>
                    <td>{n.depth}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : <p>No blast radius data available.</p>}
      </section>

      <section className="rpt-section">
        <h2>{t('report.sections.persistence')}</h2>
        {persistence ? (
          <table className="rpt-info-table">
            <tbody>
              <tr><td>Persisted</td><td><strong style={{ color: persistence.persisted ? 'var(--danger)' : 'var(--success)' }}>{persistence.persisted ? 'YES' : 'NO'}</strong></td></tr>
              <tr><td>Max deviation</td><td>{(persistence.max_deviation * 100).toFixed(1)}%</td></tr>
              <tr><td>Probes run</td><td>{persistence.probes_run}</td></tr>
              {persistence.indicators.length > 0 && <tr><td>Indicators</td><td>{persistence.indicators.join(', ')}</td></tr>}
            </tbody>
          </table>
        ) : <p>Persistence detection was not run or no data available.</p>}
      </section>

      <section className="rpt-section">
        <h2>{t('report.sections.allFindings')} ({findings.length})</h2>
        {findings.length === 0 ? (
          <p>No findings detected.</p>
        ) : (
          findings.map((ev, i) => {
            const meta = ev.metadata as Record<string, unknown>
            return (
              <div key={ev.id} className="rpt-finding">
                <div className="rpt-finding-header">
                  <span className={`rpt-badge rpt-badge--${ev.severity}`}>{ev.severity.toUpperCase()}</span>
                  <span className={`rpt-badge rpt-badge--${ev.classification}`}>{ev.classification}</span>
                  <span className="rpt-finding-id">#{i + 1} · {String(meta.payload_type ?? 'unknown')}</span>
                </div>
                {ev.node_id && <p><strong>Node:</strong> <code>{ev.node_id}</code></p>}
                {(meta.indicators as string[] | undefined)?.length ? (
                  <p><strong>Indicators:</strong> {(meta.indicators as string[]).join(', ')}</p>
                ) : null}
                {ev.payload_sent && (
                  <div className="rpt-code-block">
                    <strong>Payload:</strong>
                    <pre>{ev.payload_sent.slice(0, 400)}</pre>
                  </div>
                )}
                {ev.response_received && (
                  <div className="rpt-code-block">
                    <strong>Response excerpt:</strong>
                    <pre>{ev.response_received.slice(0, 400)}</pre>
                  </div>
                )}
              </div>
            )
          })
        )}
      </section>

      <section className="rpt-section">
        <h2>{t('report.sections.methodology')}</h2>
        <p>SPECTRA performs indirect prompt injection assessment using a catalog of {run.total_events} probe events across the following attack categories: tool misuse, context poisoning, role override, exfiltration, instruction hijacking, persistence planting, and jailbreak assistance. Payloads are adapted to the detected framework ({run.framework ?? 'unknown'}) and classified using behavioral pattern matching.</p>
      </section>

      <footer className="rpt-footer">{t('report.generatedBy')} · {new Date(run.created_at).toLocaleDateString()}</footer>
    </div>
  )
}

// ── Modal ─────────────────────────────────────────────────────────────

interface Props {
  run: RunResponse
  events: EngineEvent[]
  onClose: () => void
}

export default function ReportExport({ run, events, onClose }: Props) {
  const { t } = useTranslation()
  const [level, setLevel] = useState<Level>('executive')
  const printRef = useRef<HTMLDivElement>(null)
  const score = calculateRiskScore(run, events)

  function escapeHtml(str: string): string {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')
  }

  function handlePrint() {
    if (!printRef.current) return
    const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SPECTRA Report – ${escapeHtml(run.target_url)}</title>
  <style>
    body { font-family: 'Inter', system-ui, sans-serif; font-size: 13px; color: #0F172A; margin: 32px; }
    .rpt-header { display: flex; justify-content: space-between; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 2px solid #0F172A; }
    .rpt-logo { font-family: monospace; font-size: 20px; font-weight: 700; letter-spacing: 4px; }
    h1 { font-size: 22px; margin-bottom: 20px; }
    h2 { font-size: 15px; margin: 20px 0 10px; padding-bottom: 4px; border-bottom: 1px solid #E2E8F0; }
    .rpt-score-block { text-align: center; margin: 24px 0; }
    .rpt-score-number { font-size: 52px; font-weight: 800; line-height: 1; }
    .rpt-score-number span { font-size: 24px; color: #64748B; }
    .rpt-score-level { font-size: 13px; letter-spacing: 3px; color: #64748B; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    td, th { padding: 6px 10px; border: 1px solid #E2E8F0; }
    th { background: #F8FAFC; font-weight: 600; }
    code, pre { font-family: monospace; background: #F8FAFC; padding: 2px 4px; border-radius: 3px; font-size: 11px; }
    pre { padding: 8px; overflow: auto; max-height: 200px; white-space: pre-wrap; }
    .rpt-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-right: 4px; }
    .rpt-badge--critical { background: #FEF2F2; color: #DC2626; }
    .rpt-badge--high { background: #FFF7ED; color: #EA580C; }
    .rpt-badge--medium { background: #FFFBEB; color: #D97706; }
    .rpt-badge--low { background: #F0FDF4; color: #16A34A; }
    .rpt-badge--malicious { background: #FEF2F2; color: #DC2626; }
    .rpt-badge--suspicious { background: #FFF7ED; color: #EA580C; }
    .rpt-finding { border: 1px solid #E2E8F0; padding: 12px; margin-bottom: 12px; border-radius: 4px; }
    .rpt-finding-header { margin-bottom: 8px; }
    .rpt-footer { margin-top: 40px; padding-top: 12px; border-top: 1px solid #E2E8F0; font-size: 11px; color: #94A3B8; text-align: center; }
    ol li { margin-bottom: 8px; line-height: 1.6; }
    .rpt-bar-outer { height: 6px; background: #E2E8F0; border-radius: 3px; flex: 1; margin: 0 8px; display: inline-block; width: 100px; vertical-align: middle; }
    .rpt-bar-inner { height: 100%; background: #EF4444; border-radius: 3px; }
    .rpt-score-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
    @media print { body { margin: 20px; } }
  </style>
</head>
<body>${printRef.current.innerHTML}</body>
</html>`
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const win = window.open(url, '_blank')
    if (!win) { URL.revokeObjectURL(url); return }
    win.addEventListener('load', () => {
      win.print()
      URL.revokeObjectURL(url)
    })
  }

  function handleDownload() {
    const data = { run, events, risk_score: score, generated_at: new Date().toISOString() }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `spectra-report-${run.id.slice(0, 8)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--large" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{t('report.title')}</h2>
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>

        <div className="report-level-tabs">
          {(['executive', 'technical', 'raw'] as Level[]).map(l => (
            <button
              key={l}
              className={`report-tab${level === l ? ' report-tab--active' : ''}`}
              onClick={() => setLevel(l)}
            >
              {l === 'executive' && <FileText size={13} />}
              {l === 'technical' && <FileText size={13} />}
              {l === 'raw'       && <Code size={13} />}
              {t(`report.levels.${l}`)}
            </button>
          ))}
        </div>

        <p className="report-level-desc">{t(`report.level${level === 'executive' ? 1 : level === 'technical' ? 2 : 3}Desc`)}</p>

        <div className="report-preview" ref={printRef}>
          {level === 'executive' && <ExecutiveReport run={run} score={score} />}
          {level === 'technical' && <TechnicalReport run={run} events={events} />}
          {level === 'raw' && (
            <pre className="report-raw-json">
              {JSON.stringify({ run, risk_score: score, events_count: events.length }, null, 2)}
            </pre>
          )}
        </div>

        <div className="modal-footer">
          <Button variant="secondary" onClick={onClose}>{t('report.close')}</Button>
          {level !== 'raw' && (
            <Button onClick={handlePrint}>
              <Printer size={14} />
              {t('report.print')}
            </Button>
          )}
          {level === 'raw' && (
            <Button onClick={handleDownload}>
              <Download size={14} />
              {t('report.download')}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

function levelColor(level: string): string {
  const map: Record<string, string> = {
    low: '#22C55E', medium: '#EAB308', high: '#F97316', critical: '#EF4444', maximum: '#991B1B',
  }
  return map[level] ?? '#64748B'
}
