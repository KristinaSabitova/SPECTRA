import { useTranslation } from 'react-i18next'
import type { RiskScore, RiskLevel } from '@/types'

// ── Gauge colors ──────────────────────────────────────────────────────

const LEVEL_COLOR: Record<RiskLevel, string> = {
  low:      '#22C55E',
  medium:   '#EAB308',
  high:     '#F97316',
  critical: '#EF4444',
  maximum:  '#991B1B',
}

// ── SVG arc gauge ─────────────────────────────────────────────────────

function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number): string {
  const toRad = (d: number) => (d - 90) * (Math.PI / 180)
  const x1 = cx + r * Math.cos(toRad(startDeg))
  const y1 = cy + r * Math.sin(toRad(startDeg))
  const x2 = cx + r * Math.cos(toRad(endDeg))
  const y2 = cy + r * Math.sin(toRad(endDeg))
  const la = endDeg - startDeg > 180 ? 1 : 0
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${la} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`
}

function RiskGauge({ score, level }: { score: number; level: RiskLevel }) {
  const { t } = useTranslation()
  const color = LEVEL_COLOR[level]
  // Arc: 135° → 405° (270° total, centered at bottom)
  const START = 135
  const SPAN  = 270
  const fill  = START + (score / 100) * SPAN

  return (
    <svg viewBox="0 0 200 180" className="risk-gauge-svg">
      {/* Background track */}
      <path
        d={describeArc(100, 100, 72, START, START + SPAN)}
        fill="none"
        stroke="var(--border)"
        strokeWidth="14"
        strokeLinecap="round"
      />
      {/* Score fill */}
      {score > 0 && (
        <path
          d={describeArc(100, 100, 72, START, fill)}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          style={{ transition: 'all 0.8s ease' }}
        />
      )}
      {/* Score value */}
      <text x="100" y="100" textAnchor="middle" fontSize="36" fontWeight="700" fill={color} dy="6">
        {score}
      </text>
      <text x="100" y="126" textAnchor="middle" fontSize="12" fill="var(--text-muted)">
        {t(`risk.levels.${level}`).toUpperCase()}
      </text>
    </svg>
  )
}

// ── Score bar ─────────────────────────────────────────────────────────

function ScoreBar({ value, color, weight }: { value: number; color: string; weight: number }) {
  return (
    <div className="risk-bar-track">
      <div
        className="risk-bar-fill"
        style={{
          width: `${value}%`,
          background: color,
          opacity: 0.1 + weight * 0.9,
          transition: 'width 0.6s ease',
        }}
      />
      <span className="risk-bar-value">{Math.round(value)}</span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────

interface Props {
  score: RiskScore | null
}

const COMPONENTS: Array<{
  key: keyof Pick<RiskScore, 'surface' | 'blast' | 'persistence' | 'findings'>
  weight: number
  color: string
}> = [
  { key: 'blast',       weight: 0.40, color: '#EF4444' },
  { key: 'persistence', weight: 0.30, color: '#F97316' },
  { key: 'surface',     weight: 0.15, color: '#EAB308' },
  { key: 'findings',    weight: 0.15, color: '#8B5CF6' },
]

export default function RiskScoring({ score }: Props) {
  const { t } = useTranslation()

  if (!score) {
    return (
      <div className="risk-panel risk-panel--empty">
        <p className="risk-calculating">{t('risk.calculating')}</p>
      </div>
    )
  }

  return (
    <div className="risk-panel">
      <div className="risk-gauge-wrap">
        <RiskGauge score={score.composite} level={score.level} />
      </div>

      <div className="risk-breakdown">
        {COMPONENTS.map(({ key, weight, color }) => (
          <div key={key} className="risk-row">
            <div className="risk-row-header">
              <span className="risk-label">{t(`risk.components.${key}`)}</span>
              <span className="risk-weight">{(weight * 100).toFixed(0)}%</span>
            </div>
            <ScoreBar value={score[key]} color={color} weight={weight} />
            <p className="risk-desc">{t(`risk.${key}Desc`)}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
