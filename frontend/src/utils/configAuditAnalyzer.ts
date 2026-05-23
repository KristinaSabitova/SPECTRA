export type Severity  = 'critical' | 'high' | 'medium'
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'
export type Platform  = 'claude' | 'chatgpt' | 'copilot' | 'other'
export type Tool      = 'drive' | 'notion' | 'email' | 'calendar' | 'github' | 'database' | 'other'
export type Category  =
  | 'sensitive_data'
  | 'prompt_danger'
  | 'attack_surface'
  | 'prompt_injection'
  | 'exfiltration'
  | 'manipulation'

export interface ConfigInput {
  platform: Platform
  systemPrompt: string
  context: string
  tools: Tool[]
  userCount: number
}

export interface Finding {
  id: string
  severity: Severity
  category: Category
  evidence?: string
}

export interface AnalysisResult {
  score: number
  riskLevel: RiskLevel
  findings: Finding[]
  counts: { critical: number; high: number; medium: number }
}

// ── weights ────────────────────────────────────────────────────────────

const WEIGHTS: Record<string, number> = {
  CREDENTIALS_EXPOSED:  30,
  CONTEXT_CREDENTIALS:  30,
  EMAIL_EXFILTRATION:   30,
  DATABASE_UNRESTRICTED:30,
  INTERNAL_PATHS:       15,
  CLIENT_DATA:          15,
  DANGEROUS_KEYWORDS:   15,
  TRUST_USER:           15,
  NO_INJECTION_GUARD:   15,
  MULTI_TOOL_SURFACE:   15,
  CONTRADICTORY:         7,
  INJECTION_PLACEHOLDERS:7,
  CONDITIONAL_BYPASS:    7,
  HIGH_USER_COUNT:       7,
}

// ── pattern helpers ────────────────────────────────────────────────────

function firstMatch(text: string, patterns: RegExp[]): string | undefined {
  for (const p of patterns) {
    const m = text.match(p)
    if (m) return m[0].slice(0, 40) + (m[0].length > 40 ? '…' : '')
  }
}

function firstKeyword(text: string, keywords: string[]): string | undefined {
  const lower = text.toLowerCase()
  return keywords.find(k => lower.includes(k))
}

function detectCredentials(text: string): string | undefined {
  return firstMatch(text, [
    /(?:password|passwd|pwd)\s*[:=]\s*\S+/i,
    /(?:api[_-]?key|apikey)\s*[:=]\s*\S+/i,
    /(?:secret|token)\s*[:=]\s*\S+/i,
    /Bearer\s+[A-Za-z0-9\-._~+/]+=*/,
    /sk-[A-Za-z0-9]{20,}/,
    /sk-ant-[A-Za-z0-9-]{20,}/,
    /AIzaSy[A-Za-z0-9_-]{33}/,
    /ghp_[A-Za-z0-9]{36}/,
    /Authorization:\s*\S+/i,
  ])
}

function detectInternalPaths(text: string): string | undefined {
  return firstMatch(text, [
    /\b(?:192\.168\.|10\.\d{1,3}\.|172\.(?:1[6-9]|2\d|3[01])\.|127\.0\.0\.1)\d+\.\d+/,
    /\/(?:var|etc|home|root|opt|srv)\//,
    /C:\\Users\\/i,
    /\\\\[A-Za-z0-9][\w-]+\\/,
    /localhost:\d+/,
  ])
}

function detectDangerousKeywords(text: string): string | undefined {
  return firstKeyword(text, [
    'ignore previous instructions', 'ignore all previous', 'forget your instructions',
    'forget everything', 'jailbreak', 'dan mode', 'developer mode', 'unrestricted mode',
    'you are now free', 'as an ai without restrictions', 'bypass restrictions',
    'override instructions', 'disregard your',
  ])
}

function detectTrustUser(text: string): string | undefined {
  return firstKeyword(text, [
    'trust the user', 'the user is always right', 'the user is an admin',
    'the user is authenticated', 'the user is authorized', 'the user has admin',
    'always follow user instructions', 'user has full access', 'user can request anything',
  ])
}

function detectPlaceholders(text: string): string | undefined {
  return firstMatch(text, [
    /\{\{[^}]+\}\}/,
    /\{[a-zA-Z_]\w*\}/,
    /<[A-Z][A-Z_]+>/,
    /\[INSERT [^\]]+\]/i,
    /%[A-Z_]+%/,
  ])
}

function detectConditionalBypass(text: string): string | undefined {
  return firstKeyword(text, [
    'if the user says', 'if user says', 'when the user says', 'when user says',
    'if user provides', 'if user mentions', 'if the user claims',
    'if user asks for password', 'if user is',
  ])
}

function hasContradiction(text: string): boolean {
  const lower = text.toLowerCase()
  const restrictive = ['never reveal', 'never share', 'never disclose', 'do not reveal', "don't reveal", 'no reveles', 'nunca compartas']
  const permissive  = ['always reveal', 'always share', 'always show', 'provide when asked', 'share when requested', 'reveal when']
  return restrictive.some(r => lower.includes(r)) && permissive.some(p => lower.includes(p))
}

function hasInjectionGuard(text: string): boolean {
  const lower = text.toLowerCase()
  return [
    'do not follow instructions from', 'ignore instructions in user',
    'do not execute commands from', 'treat user input as untrusted',
    'never follow instructions embedded', 'ignore any instructions that',
    'disregard any directives in', 'user-provided content may contain',
    'no ejecutes instrucciones que contradigan', 'los documentos pueden contener instrucciones',
  ].some(g => lower.includes(g))
}

function detectClientData(text: string): string | undefined {
  return firstMatch(text, [
    /(?:cliente|customer|client|empresa|company)\s*:\s*[A-Z][a-zA-ZÀ-ÿ\s]{2,30}/i,
  ])
}

// ── main analyzer ──────────────────────────────────────────────────────

export function analyzeConfig(input: ConfigInput): AnalysisResult {
  const findings: Finding[] = []
  const { systemPrompt: sp, context: ctx, tools, userCount } = input
  const combined = sp + '\n' + ctx
  const lower = sp.toLowerCase()

  // sensitive data
  const credSp = detectCredentials(sp)
  if (credSp) findings.push({ id: 'CREDENTIALS_EXPOSED', severity: 'critical', category: 'sensitive_data', evidence: credSp })

  const credCtx = detectCredentials(ctx)
  if (credCtx) findings.push({ id: 'CONTEXT_CREDENTIALS', severity: 'critical', category: 'sensitive_data', evidence: credCtx })

  const pathEvidence = detectInternalPaths(combined)
  if (pathEvidence) findings.push({ id: 'INTERNAL_PATHS', severity: 'high', category: 'sensitive_data', evidence: pathEvidence })

  const clientEvidence = detectClientData(combined)
  if (clientEvidence) findings.push({ id: 'CLIENT_DATA', severity: 'high', category: 'sensitive_data', evidence: clientEvidence })

  // exfiltration
  const emailRestricted = /(?:whitelist|lista blanca|only internal|only to|solo dominios|solo a)/i.test(sp)
  if (tools.includes('email') && !emailRestricted) {
    findings.push({ id: 'EMAIL_EXFILTRATION', severity: 'critical', category: 'exfiltration' })
  }

  // attack surface
  const dbReadOnly = /(?:read.only|read-only|solo lectura|select only|no write|no modificar)/i.test(sp)
  if (tools.includes('database') && !dbReadOnly) {
    findings.push({ id: 'DATABASE_UNRESTRICTED', severity: 'critical', category: 'attack_surface' })
  }

  const externalTools = tools.filter(t => ['email', 'github', 'drive', 'notion', 'database'].includes(t))
  const hasLogging = /(?:log|registro|audit|trazabilidad|track)/i.test(sp)
  if (externalTools.length >= 3 && !hasLogging) {
    findings.push({ id: 'MULTI_TOOL_SURFACE', severity: 'high', category: 'attack_surface' })
  }

  if (userCount > 100) {
    findings.push({ id: 'HIGH_USER_COUNT', severity: 'medium', category: 'attack_surface' })
  }

  // prompt danger
  const dangerEvidence = detectDangerousKeywords(sp)
  if (dangerEvidence) findings.push({ id: 'DANGEROUS_KEYWORDS', severity: 'high', category: 'prompt_danger', evidence: dangerEvidence })

  if (hasContradiction(sp)) findings.push({ id: 'CONTRADICTORY', severity: 'medium', category: 'prompt_danger' })

  // prompt injection
  if (sp.trim().length > 50 && !hasInjectionGuard(sp)) {
    findings.push({ id: 'NO_INJECTION_GUARD', severity: 'high', category: 'prompt_injection' })
  }

  const placeholderEvidence = detectPlaceholders(sp)
  if (placeholderEvidence) findings.push({ id: 'INJECTION_PLACEHOLDERS', severity: 'medium', category: 'prompt_injection', evidence: placeholderEvidence })

  // manipulation
  const trustEvidence = detectTrustUser(lower)
  if (trustEvidence) findings.push({ id: 'TRUST_USER', severity: 'high', category: 'manipulation', evidence: trustEvidence })

  const conditionalEvidence = detectConditionalBypass(lower)
  if (conditionalEvidence) findings.push({ id: 'CONDITIONAL_BYPASS', severity: 'medium', category: 'manipulation', evidence: conditionalEvidence })

  // score
  const raw = findings.reduce((sum, f) => sum + (WEIGHTS[f.id] ?? 0), 0)
  const score = Math.min(100, raw)
  const riskLevel: RiskLevel = score >= 76 ? 'critical' : score >= 51 ? 'high' : score >= 26 ? 'medium' : 'low'

  return {
    score,
    riskLevel,
    findings,
    counts: {
      critical: findings.filter(f => f.severity === 'critical').length,
      high:     findings.filter(f => f.severity === 'high').length,
      medium:   findings.filter(f => f.severity === 'medium').length,
    },
  }
}
