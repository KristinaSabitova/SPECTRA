import { useState, useEffect } from 'react'
import { auditsApi } from '@/services/api'
import type { Audit } from '@/types'

export function useAudits() {
  const [audits, setAudits] = useState<Audit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    auditsApi.list()
      .then(res => setAudits(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return { audits, loading, error }
}
