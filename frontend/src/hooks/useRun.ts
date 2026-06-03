import { useState, useEffect, useCallback, useRef } from 'react'
import { engineApi } from '@/services/api'
import type { RunResponse, EngineEvent, RiskScore, RiskLevel } from '@/types'

export function calculateRiskScore(run: RunResponse, events: EngineEvent[]): RiskScore {
  const detail = run.blast_radius_detail
  const totalNodes = detail?.metadata.total_nodes ?? 1
  const cascadeDepth = detail?.cascade_depth ?? 0

  const surface = Math.min(100, totalNodes * 8 + cascadeDepth * 4)
  const blast = run.blast_radius_score ?? 0
  const persistence = run.persistence_detected ? 100 : 0

  let findingsRaw = 0
  for (const e of events) {
    if (e.event_type !== 'finding_generated') continue
    switch (e.severity) {
      case 'critical': findingsRaw += 25; break
      case 'high':     findingsRaw += 15; break
      case 'medium':   findingsRaw += 8;  break
      case 'low':      findingsRaw += 3;  break
    }
  }
  const findings = Math.min(100, findingsRaw)

  const composite = Math.round(
    surface * 0.15 + blast * 0.40 + persistence * 0.30 + findings * 0.15,
  )

  const level: RiskLevel =
    composite <= 20 ? 'low'
    : composite <= 40 ? 'medium'
    : composite <= 60 ? 'high'
    : composite <= 80 ? 'critical'
    : 'maximum'

  return { composite, surface, blast, persistence, findings, level }
}

interface UseRunResult {
  run:       RunResponse | null
  events:    EngineEvent[]
  riskScore: RiskScore | null
  loading:   boolean
  error:     string | null
  refresh:   () => void
}

export function useRun(runId: string): UseRunResult {
  const [run, setRun]       = useState<RunResponse | null>(null)
  const [events, setEvents] = useState<EngineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)
  const stopStream = useRef<(() => void) | null>(null)
  const isLive = useRef(false)

  const loadInitial = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [runRes, eventsRes] = await Promise.all([
        engineApi.getRun(runId),
        engineApi.getEvents(runId, 1000),
      ])
      setRun(runRes.data)
      setEvents(eventsRes.data)

      if (runRes.data.status === 'queued' || runRes.data.status === 'running') {
        isLive.current = true
        stopStream.current = engineApi.streamEvents(
          runId,
          (ev) => setEvents((prev) => {
            if (prev.find(e => e.id === ev.id)) return prev
            return [...prev, ev]
          }),
          () => {
            isLive.current = false
            engineApi.getRun(runId).then(r => setRun(r.data)).catch(() => {})
          },
        )
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => {
    loadInitial()
    return () => { stopStream.current?.() }
  }, [loadInitial])

  const riskScore = run ? calculateRiskScore(run, events) : null

  return { run, events, riskScore, loading, error, refresh: loadInitial }
}
