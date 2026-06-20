import { useState, useCallback } from 'react'
import { publicApi } from '@/services/api'
import type { ConfigScanResponse, ScanFinding } from '@/types'

const SEV_ORDER = ['critical', 'high', 'medium', 'low', 'info'] as const
const SEV_COLOR: Record<string, string> = {
  critical: '#DC2626',
  high: '#D97706',
  medium: '#F59E0B',
  low: '#10B981',
  info: '#6B7280',
  safe: '#10B981',
}

function RiskGauge({ score, riskLevel }: { score: number; riskLevel: string }) {
  const color = SEV_COLOR[riskLevel] ?? '#9CA3AF'
  const total = 157.08
  const dash = (score / 100) * total
  return (
    <div style={{ textAlign: 'center' }}>
      <svg width="160" height="96" viewBox="0 0 160 96" style={{ display: 'block', margin: '0 auto' }}>
        <path d="M14,80 A66,66 0 0,1 146,80" fill="none" stroke="#E5E7EB" strokeWidth="14" strokeLinecap="round" />
        <path
          d="M14,80 A66,66 0 0,1 146,80"
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${(dash / 157.08) * 207} 207`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        <text x="80" y="76" textAnchor="middle" fontSize="32" fontWeight="800" fill={color}>{score}</text>
        <text x="80" y="92" textAnchor="middle" fontSize="11" fontWeight="600" fill={color} letterSpacing="1">{riskLevel.toUpperCase()}</text>
      </svg>
    </div>
  )
}

function FindingCard({ f }: { f: ScanFinding; index?: number }) {
  const [expanded, setExpanded] = useState(false)
  const color = SEV_COLOR[f.severity] ?? '#6B7280'
  return (
    <div style={{
      border: `1px solid ${color}30`,
      borderLeft: `3px solid ${color}`,
      borderRadius: '8px',
      background: '#fff',
      padding: '14px 16px',
      marginBottom: '10px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: expanded ? '12px' : 0 }}>
        <span style={{
          background: `${color}15`,
          color,
          border: `1px solid ${color}40`,
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 700,
          padding: '2px 8px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          flexShrink: 0,
        }}>{f.severity}</span>
        <span style={{ fontWeight: 600, fontSize: '13.5px', flex: 1 }}>{f.title}</span>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: 'none', border: '1px solid #E5E7EB', borderRadius: '4px',
            cursor: 'pointer', fontSize: '11px', color: '#6B7280', padding: '2px 8px',
          }}
        >{expanded ? 'Collapse' : 'Details'}</button>
      </div>
      {expanded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Trigger fragment</div>
            <code style={{
              display: 'block',
              background: '#F3F4F6',
              border: '1px solid #E5E7EB',
              borderRadius: '6px',
              padding: '8px 10px',
              fontFamily: 'monospace',
              fontSize: '12px',
              color: '#374151',
              wordBreak: 'break-all',
            }}>{f.fragment}</code>
          </div>
          <div>
            <div style={{ fontSize: '11px', fontWeight: 600, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>Suggested fix</div>
            <p style={{ fontSize: '13px', color: '#374151', lineHeight: 1.6, margin: 0 }}>{f.suggestion}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Scan() {
  const [prompt, setPrompt] = useState('')
  const [result, setResult] = useState<ConfigScanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleScan = useCallback(async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError('')
    try {
      const { data } = await publicApi.configScan(prompt)
      setResult(data)
    } catch (e: any) {
      if (e.response?.status === 429) {
        setError('Rate limit exceeded. Try again in a few minutes.')
      } else {
        setError(e.response?.data?.detail ?? 'Scan failed. Try again.')
      }
    } finally {
      setLoading(false)
    }
  }, [prompt])

  const copyMarkdown = useCallback(() => {
    if (!result) return
    const md = [
      `# SPECTRA Config Scan Results`,
      `**Score:** ${result.score}/100  **Risk:** ${result.risk_level.toUpperCase()}`,
      '',
      '## Findings',
      ...result.findings.map(f =>
        `### [${f.severity.toUpperCase()}] ${f.title}\n**Fragment:** \`${f.fragment}\`\n**Fix:** ${f.suggestion}`
      ),
    ].join('\n\n')
    navigator.clipboard.writeText(md)
  }, [result])

  return (
    <div style={{ minHeight: '100vh', background: '#F8F9FA', padding: '40px 24px' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <span style={{
              fontFamily: 'monospace', fontSize: '18px', fontWeight: 700,
              letterSpacing: '4px', color: '#2563EB',
            }}>SPECTRA</span>
            <span style={{ color: '#E5E7EB', fontSize: '20px' }}>·</span>
            <span style={{ fontSize: '16px', fontWeight: 600, color: '#374151' }}>Config Scanner</span>
          </div>
          <p style={{ fontSize: '14px', color: '#6B7280', margin: 0 }}>
            Analyze your AI agent's system prompt for security vulnerabilities.
            No account required. Your prompt is never stored.
          </p>
        </div>

        {/* Input */}
        <div style={{
          background: '#fff', border: '1px solid #E5E7EB', borderRadius: '12px',
          padding: '20px', marginBottom: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        }}>
          <label style={{ fontSize: '13px', fontWeight: 500, color: '#374151', display: 'block', marginBottom: '8px' }}>
            System Prompt <span style={{ color: '#9CA3AF', fontWeight: 400 }}>(max 10,000 chars)</span>
          </label>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="Paste your AI agent's system prompt here..."
            maxLength={10000}
            style={{
              width: '100%', minHeight: '180px', padding: '12px',
              border: '1.5px solid #E5E7EB', borderRadius: '8px',
              fontFamily: 'monospace', fontSize: '13px', resize: 'vertical',
              outline: 'none', color: '#111', lineHeight: 1.6,
            }}
            onFocus={e => e.target.style.borderColor = '#2563EB'}
            onBlur={e => e.target.style.borderColor = '#E5E7EB'}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
            <span style={{ fontSize: '12px', color: '#9CA3AF' }}>{prompt.length.toLocaleString()} / 10,000</span>
            <button
              onClick={handleScan}
              disabled={loading || !prompt.trim()}
              style={{
                background: '#2563EB', color: '#fff', border: 'none', borderRadius: '8px',
                padding: '10px 24px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
                opacity: (loading || !prompt.trim()) ? 0.5 : 1, transition: 'opacity 0.12s',
              }}
            >
              {loading ? 'Scanning…' : 'Scan Prompt'}
            </button>
          </div>
          {error && (
            <div style={{
              marginTop: '12px', background: '#FEF2F2', border: '1px solid #FECACA',
              borderRadius: '6px', padding: '10px 12px', fontSize: '13px', color: '#DC2626',
            }}>{error}</div>
          )}
        </div>

        {/* Results */}
        {result && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Score card */}
            <div style={{
              background: '#fff', border: '1px solid #E5E7EB', borderRadius: '12px',
              padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            }}>
              <div style={{ display: 'flex', gap: '24px', alignItems: 'stretch', flexWrap: 'wrap' }}>
                <div style={{ flex: '0 0 160px' }}>
                  <RiskGauge score={result.score} riskLevel={result.risk_level} />
                </div>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <span style={{ fontSize: '15px', fontWeight: 700, color: '#111' }}>Scan Results</span>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={copyMarkdown}
                        style={{
                          background: '#F3F4F6', border: '1px solid #E5E7EB', borderRadius: '6px',
                          padding: '5px 12px', fontSize: '12px', cursor: 'pointer', color: '#374151',
                        }}
                      >Copy as Markdown</button>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {SEV_ORDER.filter(s => result.findings.some(f => f.severity === s)).map(sev => {
                      const count = result.findings.filter(f => f.severity === sev).length
                      const color = SEV_COLOR[sev]
                      return (
                        <div key={sev} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{
                            width: '60px', fontSize: '11px', fontWeight: 700,
                            textTransform: 'uppercase', color,
                          }}>{sev}</span>
                          <div style={{ flex: 1, height: '6px', background: '#F3F4F6', borderRadius: '3px' }}>
                            <div style={{
                              height: '100%', background: color, borderRadius: '3px',
                              width: `${Math.min(100, count * 20)}%`, transition: 'width 0.5s ease',
                            }} />
                          </div>
                          <span style={{ fontSize: '12px', fontWeight: 700, color, width: '20px', textAlign: 'right' }}>{count}</span>
                        </div>
                      )
                    })}
                    {result.findings.length === 0 && (
                      <p style={{ fontSize: '14px', color: '#10B981', fontWeight: 600, margin: 0 }}>
                        No issues found. Your prompt looks secure.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Findings list */}
            {result.findings.length > 0 && (
              <div style={{
                background: '#fff', border: '1px solid #E5E7EB', borderRadius: '12px',
                padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
              }}>
                <h2 style={{ fontSize: '14px', fontWeight: 700, color: '#111', marginBottom: '16px' }}>
                  {result.findings.length} Finding{result.findings.length !== 1 ? 's' : ''}
                </h2>
                {result.findings.map((f, i) => (
                  <FindingCard key={i} f={f} index={i} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div style={{ marginTop: '48px', textAlign: 'center', fontSize: '12px', color: '#9CA3AF' }}>
          <a href="/login" style={{ color: '#2563EB', textDecoration: 'none' }}>Sign in</a>
          {' '}for full AI agent security testing · SPECTRA
        </div>
      </div>
    </div>
  )
}
