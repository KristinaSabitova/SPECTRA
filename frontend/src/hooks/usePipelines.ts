import { useState, useEffect, useCallback } from 'react'
import { pipelinesApi } from '@/services/api'
import type { Pipeline } from '@/types'

export function usePipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    pipelinesApi.list()
      .then(res => setPipelines(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  return { pipelines, loading, error, refresh: load }
}
