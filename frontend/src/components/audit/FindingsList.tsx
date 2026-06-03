import { useState, Fragment } from 'react'
import { useTranslation } from 'react-i18next'
import { ShieldOff, ChevronRight } from 'lucide-react'
import Badge from '@/components/common/Badge'
import EmptyState from '@/components/common/EmptyState'
import type { EngineEvent, Severity } from '@/types'

interface ForensicMatch {
  pattern_name: string
  line_number:  number
  line_excerpt: string
  matched_text: string
}

function severityOrder(s: Severity): number {
  return { critical: 0, high: 1, medium: 2, low: 3, info: 4 }[s] ?? 5
}

interface Props {
  events: EngineEvent[]
}

export default function FindingsList({ events }: Props) {
  const { t } = useTranslation()
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const findings = events
    .filter(e => e.event_type === 'finding_generated')
    .sort((a, b) => severityOrder(a.severity) - severityOrder(b.severity))

  if (findings.length === 0) {
    return (
      <EmptyState
        icon={ShieldOff}
        title={t('findings.noFindings')}
        description={t('findings.noFindingsDesc')}
      />
    )
  }

  return (
    <div className="table-wrapper">
      <table className="table">
        <thead>
          <tr>
            <th style={{ width: 28 }}></th>
            <th>{t('findings.columns.severity')}</th>
            <th>{t('findings.columns.type')}</th>
            <th>{t('findings.columns.classification')}</th>
            <th>{t('findings.columns.node')}</th>
            <th>{t('findings.columns.indicators')}</th>
          </tr>
        </thead>
        <tbody>
          {findings.map(ev => {
            const meta            = ev.metadata as Record<string, unknown>
            const payloadType     = String(meta.payload_type ?? '')
            const indicators      = (meta.indicators       as string[]       | undefined) ?? []
            const payloadDesc     = (meta.payload_description as string      | undefined) ?? ''
            const reasoning       = (meta.forensic_reasoning  as string      | undefined) ?? ''
            const forensicMatches = (meta.forensic_matches    as ForensicMatch[] | undefined) ?? []
            const isExpanded      = expandedId === ev.id
            const hasDetail       = !!(payloadDesc || reasoning || forensicMatches.length)

            return (
              <Fragment key={ev.id}>
                <tr
                  className={`finding-row--clickable${isExpanded ? ' finding-row--expanded' : ''}`}
                  onClick={() => hasDetail && setExpandedId(isExpanded ? null : ev.id)}
                >
                  <td style={{ paddingRight: 0 }}>
                    {hasDetail && (
                      <ChevronRight
                        size={14}
                        className={`finding-expand-icon${isExpanded ? ' finding-expand-icon--open' : ''}`}
                      />
                    )}
                  </td>
                  <td>
                    <Badge variant={ev.severity} label={t(`audits.severity.${ev.severity}`)} />
                  </td>
                  <td>
                    <span className="finding-type">
                      {t(`findings.payloadTypes.${payloadType}`, payloadType)}
                    </span>
                  </td>
                  <td>
                    <Badge
                      variant={ev.classification as Severity}
                      label={t(`findings.classifications.${ev.classification}`)}
                    />
                  </td>
                  <td className="mono">{ev.node_id ? truncate(ev.node_id, 32) : '—'}</td>
                  <td>
                    {indicators.length > 0 ? (
                      <div className="indicators-list">
                        {indicators.slice(0, 2).map((ind, i) => (
                          <code key={i} className="indicator-chip">{truncate(ind, 40)}</code>
                        ))}
                        {indicators.length > 2 && (
                          <span className="indicator-more">+{indicators.length - 2}</span>
                        )}
                      </div>
                    ) : '—'}
                  </td>
                </tr>

                {isExpanded && (
                  <tr className="finding-detail-row">
                    <td colSpan={6}>
                      <div className="finding-detail-panel">
                        {payloadDesc && (
                          <div className="finding-detail-section">
                            <span className="finding-detail-label">
                              {t('findings.detail.description', 'Payload description')}
                            </span>
                            <p className="finding-detail-desc">{payloadDesc}</p>
                          </div>
                        )}

                        {reasoning && (
                          <div className="finding-detail-section">
                            <span className="finding-detail-label">
                              {t('findings.detail.reasoning', 'Forensic reasoning')}
                            </span>
                            <pre className="finding-detail-reasoning">{reasoning}</pre>
                          </div>
                        )}

                        {forensicMatches.length > 0 && (
                          <div className="finding-detail-section">
                            <span className="finding-detail-label">
                              {t('findings.detail.matches', 'Forensic matches')} ({forensicMatches.length})
                            </span>
                            <div className="forensic-match-list">
                              {forensicMatches.map((m, i) => (
                                <div key={i} className="forensic-match-item">
                                  <span className="forensic-match-line">L{m.line_number}</span>
                                  <div className="forensic-match-body">
                                    <span className="forensic-match-pattern">{m.pattern_name}</span>
                                    <code className="forensic-match-text">{m.matched_text}</code>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}
