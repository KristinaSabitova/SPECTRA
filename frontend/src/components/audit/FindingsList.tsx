import { useTranslation } from 'react-i18next'
import { ShieldOff } from 'lucide-react'
import Badge from '@/components/common/Badge'
import EmptyState from '@/components/common/EmptyState'
import type { EngineEvent, Severity } from '@/types'

function severityOrder(s: Severity): number {
  return { critical: 0, high: 1, medium: 2, low: 3, info: 4 }[s] ?? 5
}

interface Props {
  events: EngineEvent[]
}

export default function FindingsList({ events }: Props) {
  const { t } = useTranslation()

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
            <th>{t('findings.columns.severity')}</th>
            <th>{t('findings.columns.type')}</th>
            <th>{t('findings.columns.classification')}</th>
            <th>{t('findings.columns.node')}</th>
            <th>{t('findings.columns.indicators')}</th>
          </tr>
        </thead>
        <tbody>
          {findings.map(ev => {
            const meta = ev.metadata as Record<string, unknown>
            const payloadType  = String(meta.payload_type ?? '')
            const indicators   = (meta.indicators as string[] | undefined) ?? []
            return (
              <tr key={ev.id}>
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
