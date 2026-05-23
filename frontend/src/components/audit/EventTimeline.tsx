import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Info, Zap, Eye, Search } from 'lucide-react'
import type { EngineEvent, EngineEventType, Severity } from '@/types'

// ── Event type meta ───────────────────────────────────────────────────

const EVENT_ICON: Partial<Record<EngineEventType, React.ElementType>> = {
  run_started:        Zap,
  recon_started:      Search,
  recon_completed:    Search,
  payload_injected:   AlertTriangle,
  finding_generated:  AlertTriangle,
  blast_computed:     Eye,
  persistence_check:  Eye,
  run_completed:      CheckCircle,
  error:              AlertTriangle,
}

const SEVERITY_DOT: Record<Severity, string> = {
  critical: 'var(--danger)',
  high:     '#F97316',
  medium:   'var(--warning)',
  low:      '#22C55E',
  info:     'var(--text-muted)',
}

// ── Single event row ──────────────────────────────────────────────────

function EventRow({ event }: { event: EngineEvent }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const Icon = EVENT_ICON[event.event_type] ?? Info
  const hasDetail = event.payload_sent || event.response_received || (event.metadata && Object.keys(event.metadata).length > 0)
  const isFinding = event.event_type === 'finding_generated'
  const isError   = event.event_type === 'error'

  return (
    <div className={`tl-row${isFinding ? ' tl-row--finding' : ''}${isError ? ' tl-row--error' : ''}`}>
      <div className="tl-row-left">
        <span className="tl-dot" style={{ background: SEVERITY_DOT[event.severity] }} />
        <span className="tl-line" />
      </div>
      <div className="tl-row-body">
        <div className="tl-row-header">
          <span className="tl-icon-wrap" style={{ color: SEVERITY_DOT[event.severity] }}>
            <Icon size={13} />
          </span>
          <span className="tl-event-type">
            {t(`timeline.eventTypes.${event.event_type}`, event.event_type)}
          </span>
          {event.node_id && (
            <span className="tl-node mono">{truncate(event.node_id, 36)}</span>
          )}
          {event.duration_ms != null && (
            <span className="tl-duration">{event.duration_ms} {t('run.ms')}</span>
          )}
          <span className="tl-seq">#{event.sequence}</span>
          <span className="tl-time mono">{formatTime(event.timestamp)}</span>
          {hasDetail && (
            <button className="tl-expand-btn" onClick={() => setExpanded(v => !v)}>
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? t('timeline.hidePayload') : t('timeline.showPayload')}
            </button>
          )}
        </div>

        {expanded && (
          <div className="tl-detail">
            {event.payload_sent && (
              <div className="tl-code-block">
                <span className="tl-code-label">{t('timeline.payload')}</span>
                <pre className="tl-code">{event.payload_sent.slice(0, 800)}</pre>
              </div>
            )}
            {event.response_received && (
              <div className="tl-code-block">
                <span className="tl-code-label">{t('timeline.response')}</span>
                <pre className="tl-code">{event.response_received.slice(0, 800)}</pre>
              </div>
            )}
            {event.metadata && Object.keys(event.metadata).length > 0 && (
              <div className="tl-code-block">
                <span className="tl-code-label">Metadata</span>
                <pre className="tl-code">{JSON.stringify(event.metadata, null, 2).slice(0, 600)}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Timeline component ────────────────────────────────────────────────

interface Props {
  events: EngineEvent[]
  isLive?: boolean
}

export default function EventTimeline({ events, isLive }: Props) {
  const { t } = useTranslation()

  if (events.length === 0) {
    return (
      <div className="tl-empty">
        <p className="tl-empty-title">{t('timeline.noEvents')}</p>
        <p className="tl-empty-desc">{t('timeline.noEventsDesc')}</p>
      </div>
    )
  }

  return (
    <div className="tl-container">
      {isLive && (
        <div className="tl-live-banner">
          <span className="tl-live-dot" />
          {t('run.liveIndicator')}
        </div>
      )}
      <div className="tl-list">
        {events.map(ev => <EventRow key={ev.id} event={ev} />)}
      </div>
    </div>
  )
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch { return iso }
}

function truncate(s: string, n: number): string {
  return s.length > n ? '…' + s.slice(-n) : s
}
