import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Printer, RotateCcw } from 'lucide-react'
import { analyzeConfig, type ConfigInput, type Finding, type Platform, type Tool } from '@/utils/configAuditAnalyzer'
import type { AnalysisResult } from '@/utils/configAuditAnalyzer'
import Button from '@/components/common/Button'

const PLATFORMS: Platform[] = ['claude', 'chatgpt', 'copilot', 'other']
const TOOLS: Tool[]          = ['drive', 'notion', 'email', 'calendar', 'github', 'database', 'other']

const SEV_STYLE = {
  critical: { bg: 'rgba(239,68,68,0.07)',  border: 'rgba(239,68,68,0.28)',  dot: '#ef4444' },
  high:     { bg: 'rgba(249,115,22,0.07)', border: 'rgba(249,115,22,0.28)', dot: '#f97316' },
  medium:   { bg: 'rgba(245,158,11,0.07)', border: 'rgba(245,158,11,0.28)', dot: '#f59e0b' },
} as const

const RISK_COLOR = { low: '#22c55e', medium: '#f59e0b', high: '#f97316', critical: '#ef4444' } as const

// ── Score gauge ───────────────────────────────────────────────────────

function ScoreGauge({ score, riskLevel }: { score: number; riskLevel: string }) {
  const r = 38
  const c = 2 * Math.PI * r
  const color = RISK_COLOR[riskLevel as keyof typeof RISK_COLOR] ?? '#64748b'
  return (
    <svg width="110" height="110" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={r} fill="none" stroke="var(--border)" strokeWidth="7" />
      <circle
        cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="7"
        strokeDasharray={`${c}`} strokeDashoffset={c - (score / 100) * c}
        strokeLinecap="round" transform="rotate(-90 50 50)"
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
      <text x="50" y="47" textAnchor="middle" dominantBaseline="middle"
        fill="var(--text)" fontSize="22" fontWeight="700">{score}</text>
      <text x="50" y="63" textAnchor="middle" dominantBaseline="middle"
        fill="var(--text-muted)" fontSize="10">/100</text>
    </svg>
  )
}

// ── Finding card ──────────────────────────────────────────────────────

function FindingCard({ finding }: { finding: Finding }) {
  const { t } = useTranslation()
  const s = SEV_STYLE[finding.severity]
  return (
    <div style={{
      background: s.bg, border: `1px solid ${s.border}`,
      borderRadius: 'var(--r-lg)', padding: '14px 16px', marginBottom: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6,
          color: s.dot,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.dot }} />
          {t(`configAudit.severity.${finding.severity}`)}
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          · {t(`configAudit.categories.${finding.category}`)}
        </span>
      </div>

      <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text)', marginBottom: 4 }}>
        {t(`configAudit.findings.${finding.id}.title`)}
      </p>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.65, marginBottom: 8 }}>
        {t(`configAudit.findings.${finding.id}.desc`)}
      </p>

      {finding.evidence && (
        <div style={{ marginBottom: 8 }}>
          <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, color: 'var(--text-muted)' }}>
            {t('configAudit.report.evidence')}
          </span>
          <code style={{
            display: 'block', marginTop: 3, padding: '5px 10px',
            background: 'var(--bg)', border: '1px solid var(--border)',
            borderRadius: 'var(--r-md)', fontSize: 12, fontFamily: 'var(--mono)',
            color: s.dot, wordBreak: 'break-all',
          }}>
            {finding.evidence}
          </code>
        </div>
      )}

      <div style={{ borderTop: `1px solid ${s.border}`, paddingTop: 8, marginTop: 2 }}>
        <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, color: 'var(--text-muted)' }}>
          {t('configAudit.report.recommendation')}
        </span>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.65, marginTop: 3 }}>
          {t(`configAudit.findings.${finding.id}.rec`)}
        </p>
      </div>
    </div>
  )
}

// ── Report ────────────────────────────────────────────────────────────

function AuditReport({
  result, input, onReset,
}: { result: AnalysisResult; input: ConfigInput; onReset: () => void }) {
  const { t } = useTranslation()
  const riskColor = RISK_COLOR[result.riskLevel]

  const grouped = {
    critical: result.findings.filter(f => f.severity === 'critical'),
    high:     result.findings.filter(f => f.severity === 'high'),
    medium:   result.findings.filter(f => f.severity === 'medium'),
  }

  return (
    <div>
      {/* header */}
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{t('configAudit.report.title')}</h1>
          <p className="page-subtitle" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {t('configAudit.report.generatedAt')} {new Date().toLocaleString()} ·{' '}
            {t(`configAudit.form.platforms.${input.platform}`)} ·{' '}
            {input.tools.length > 0 && `${input.tools.length} ${t('configAudit.report.tools')}`}
            {input.userCount > 0 && ` · ${input.userCount} ${t('configAudit.report.users')}`}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={() => window.print()}>
            <Printer size={14} />
            {t('configAudit.report.print')}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={onReset}>
            <RotateCcw size={14} />
            {t('configAudit.report.newAudit')}
          </button>
        </div>
      </div>

      {/* score summary */}
      <div className="table-wrapper" style={{ padding: '20px 24px', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
          <ScoreGauge score={result.score} riskLevel={result.riskLevel} />

          <div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              {t('configAudit.report.riskLevel')}
            </p>
            <p style={{ fontSize: 22, fontWeight: 700, color: riskColor }}>
              {t(`configAudit.riskLevel.${result.riskLevel}`)}
            </p>
          </div>

          <div style={{ display: 'flex', gap: 24 }}>
            {(['critical', 'high', 'medium'] as const).map(sev => (
              result.counts[sev] > 0 && (
                <div key={sev} style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: 26, fontWeight: 700, color: SEV_STYLE[sev].dot, lineHeight: 1 }}>
                    {result.counts[sev]}
                  </p>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {t(`configAudit.severity.${sev}`)}
                  </p>
                </div>
              )
            ))}
          </div>
        </div>
      </div>

      {/* findings */}
      {result.findings.length === 0 ? (
        <div className="table-wrapper" style={{ padding: '32px 24px', textAlign: 'center' }}>
          <p style={{ fontWeight: 600, color: 'var(--text)' }}>{t('configAudit.report.noFindings')}</p>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>{t('configAudit.report.noFindingsDesc')}</p>
        </div>
      ) : (
        <>
          {(['critical', 'high', 'medium'] as const).map(sev =>
            grouped[sev].length > 0 && (
              <div key={sev} style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: SEV_STYLE[sev].dot, display: 'inline-block',
                  }} />
                  <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {t(`configAudit.severity.${sev}`)} ({grouped[sev].length})
                  </h3>
                </div>
                {grouped[sev].map(f => <FindingCard key={f.id} finding={f} />)}
              </div>
            )
          )}
        </>
      )}
    </div>
  )
}

// ── Form ──────────────────────────────────────────────────────────────

function AuditForm({ onResult }: { onResult: (r: AnalysisResult, i: ConfigInput) => void }) {
  const { t } = useTranslation()

  const [platform,     setPlatform]     = useState<Platform>('chatgpt')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [context,      setContext]      = useState('')
  const [tools,        setTools]        = useState<Tool[]>([])
  const [userCount,    setUserCount]    = useState<number>(0)
  const [analyzing,    setAnalyzing]    = useState(false)
  const [error,        setError]        = useState('')

  function toggleTool(tool: Tool) {
    setTools(prev => prev.includes(tool) ? prev.filter(t => t !== tool) : [...prev, tool])
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!systemPrompt.trim()) { setError(t('configAudit.form.errors.promptRequired')); return }
    setError('')
    setAnalyzing(true)
    const input: ConfigInput = { platform, systemPrompt, context, tools, userCount }
    setTimeout(() => {
      onResult(analyzeConfig(input), input)
      setAnalyzing(false)
    }, 700)
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{t('configAudit.title')}</h1>
          <p className="page-subtitle">{t('configAudit.subtitle')}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="table-wrapper" style={{ padding: '20px 24px', marginBottom: 16 }}>
          <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 20 }}>
            {t('configAudit.form.title')}
          </h2>

          {error && (
            <div style={{
              padding: '10px 14px', marginBottom: 16, borderRadius: 'var(--r-md)',
              background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)',
              fontSize: 13, color: '#ef4444',
            }}>{error}</div>
          )}

          {/* platform */}
          <div className="form-group">
            <label className="form-label">{t('configAudit.form.platform')}</label>
            <select className="form-input" value={platform} onChange={e => setPlatform(e.target.value as Platform)}>
              {PLATFORMS.map(p => (
                <option key={p} value={p}>{t(`configAudit.form.platforms.${p}`)}</option>
              ))}
            </select>
          </div>

          {/* system prompt */}
          <div className="form-group">
            <label className="form-label">{t('configAudit.form.systemPrompt')}</label>
            <textarea
              className="form-input"
              rows={8}
              value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)}
              placeholder={t('configAudit.form.systemPromptPlaceholder')}
              style={{ resize: 'vertical', fontFamily: 'var(--mono)', fontSize: 12 }}
            />
          </div>

          {/* context */}
          <div className="form-group">
            <label className="form-label">{t('configAudit.form.context')}</label>
            <textarea
              className="form-input"
              rows={4}
              value={context}
              onChange={e => setContext(e.target.value)}
              placeholder={t('configAudit.form.contextPlaceholder')}
              style={{ resize: 'vertical', fontSize: 13 }}
            />
          </div>

          {/* tools */}
          <div className="form-group">
            <label className="form-label">{t('configAudit.form.tools')}</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px 12px', marginTop: 4 }}>
              {TOOLS.map(tool => (
                <label key={tool} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  cursor: 'pointer', fontSize: 13, color: 'var(--text-secondary)',
                  padding: '7px 10px', borderRadius: 'var(--r-md)',
                  border: `1px solid ${tools.includes(tool) ? 'var(--accent)' : 'var(--border)'}`,
                  background: tools.includes(tool) ? 'rgba(99,102,241,0.07)' : 'transparent',
                  userSelect: 'none',
                }}>
                  <input
                    type="checkbox"
                    checked={tools.includes(tool)}
                    onChange={() => toggleTool(tool)}
                    style={{ accentColor: 'var(--accent)' }}
                  />
                  {t(`configAudit.form.toolList.${tool}`)}
                </label>
              ))}
            </div>
          </div>

          {/* user count */}
          <div className="form-group" style={{ maxWidth: 240 }}>
            <label className="form-label">{t('configAudit.form.userCount')}</label>
            <input
              type="number"
              className="form-input"
              min={0}
              value={userCount || ''}
              onChange={e => setUserCount(Number(e.target.value) || 0)}
              placeholder={t('configAudit.form.userCountPlaceholder')}
            />
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" loading={analyzing}>
            {analyzing ? t('configAudit.form.submitting') : t('configAudit.form.submit')}
          </Button>
        </div>
      </form>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────

export default function ConfigAudit() {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [input,  setInput]  = useState<ConfigInput | null>(null)

  function handleResult(r: AnalysisResult, i: ConfigInput) {
    setResult(r)
    setInput(i)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleReset() {
    setResult(null)
    setInput(null)
  }

  if (result && input) {
    return <AuditReport result={result} input={input} onReset={handleReset} />
  }
  return <AuditForm onResult={handleResult} />
}
