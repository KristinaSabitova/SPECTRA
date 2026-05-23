// ── Auth ──────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'senior' | 'junior'

export interface UserResponse {
  id: string
  email: string
  username: string
  role: UserRole
  is_active: boolean
  is_temporary_password: boolean
  totp_enabled: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface LoginResponse {
  requires_2fa: boolean
  must_change_password?: boolean
  temp_token?: string
  tokens?: TokenResponse
  user?: UserResponse
}

export interface TOTPSetupResponse {
  secret: string
  qr_uri: string
  backup_codes: string[]
}

export interface CreateUserResponse {
  user: UserResponse
  temp_password: string
}

// ── Legacy domain ─────────────────────────────────────────────────────

export interface Agent {
  id: string
  name: string
  description?: string
  endpoint_url?: string
  created_at: string
}

export type Framework = 'langchain' | 'autogen' | 'n8n' | 'other'

export interface Pipeline {
  id: string
  name: string
  description?: string
  endpoint_url?: string
  framework?: string
  definition?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type AuditStatus = 'pending' | 'running' | 'completed' | 'failed'
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface Audit {
  id: string
  pipeline_id: string
  pipeline_name: string
  name: string | null
  status: AuditStatus
  findings_count: number
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface Finding {
  type: string
  severity: Severity
  description: string
  agent_id?: string
  evidence: Record<string, unknown>
}

export interface Report {
  audit_id: string
  total_findings: number
  severity_summary: Partial<Record<Severity, number>>
  findings: Finding[]
}

export interface ReportListItem {
  id: string
  audit_name: string | null
  pipeline_name: string
  findings_count: number
  blast_radius_score: number | null
  persistence_detected: boolean
  completed_at: string | null
  generated_at: string
}

// ── Engine types ──────────────────────────────────────────────────────

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export type EngineEventType =
  | 'run_started' | 'recon_started' | 'recon_completed'
  | 'probe_sent' | 'response_received' | 'payload_injected'
  | 'tool_detected' | 'finding_generated' | 'blast_computed'
  | 'persistence_check' | 'run_completed' | 'error'

export type Classification = 'benign' | 'suspicious' | 'malicious' | 'unknown'

export interface GraphNodeDetail {
  id: string
  label: string
  type: string
  criticality: number
  depth: number
}

export interface GraphEdgeDetail {
  src: string
  dst: string
}

export interface BlastRadiusDetail {
  score: number
  affected_nodes: string[]
  cascade_depth: number
  entry_node: string
  node_details: GraphNodeDetail[]
  edges: GraphEdgeDetail[]
  metadata: {
    reachability_ratio: number
    cascade_score: number
    edge_density: number
    critical_node_hit: boolean
    total_nodes: number
  }
}

export interface PersistenceDetail {
  persisted: boolean
  max_deviation: number
  avg_deviation: number
  deviation_by_probe: Record<string, number>
  indicators: string[]
  probes_run: number
}

export interface RunResponse {
  id: string
  target_url: string
  framework: string | null
  status: RunStatus
  config: Record<string, unknown>
  total_events: number
  findings_count: number
  blast_radius_score: number | null
  blast_radius_detail: BlastRadiusDetail | null
  persistence_detected: boolean
  persistence_detail: PersistenceDetail | null
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface EngineEvent {
  id: string
  run_id: string
  sequence: number
  event_type: EngineEventType
  node_id: string | null
  payload_sent: string | null
  response_received: string | null
  classification: Classification
  severity: Severity
  duration_ms: number | null
  metadata: Record<string, unknown>
  timestamp: string
}

export interface CreateRunRequest {
  target_url: string
  payload_types?: string[]
  mutation_strategies?: string[]
  request_timeout?: number
  auth_headers?: Record<string, string>
  check_persistence?: boolean
  max_payloads?: number
}

// ── Risk scoring ──────────────────────────────────────────────────────

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical' | 'maximum'

export interface RiskScore {
  composite: number
  surface: number
  blast: number
  persistence: number
  findings: number
  level: RiskLevel
}
