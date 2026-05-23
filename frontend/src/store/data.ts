import { create } from 'zustand'
import { auditsApi, pipelinesApi, reportsApi } from '@/services/api'
import type { Audit, Pipeline, ReportListItem } from '@/types'

interface DataState {
  pipelines:  Pipeline[]
  audits:     Audit[]
  reports:    ReportListItem[]
  loading:    boolean
  loaded:     boolean

  load:          () => Promise<void>
  addPipeline:   (p: Pipeline) => void
  removePipeline:(id: string)  => void
  addAudit:      (a: Audit)    => void
  removeAudit:   (id: string)  => void
}

export const useDataStore = create<DataState>()((set, get) => ({
  pipelines: [],
  audits:    [],
  reports:   [],
  loading:   false,
  loaded:    false,

  load: async () => {
    set({ loading: true })
    const [p, a, r] = await Promise.allSettled([
      pipelinesApi.list().then(res => res.data),
      auditsApi.list().then(res => res.data),
      reportsApi.list().then(res => res.data),
    ])
    set({
      pipelines: p.status === 'fulfilled' ? p.value : get().pipelines,
      audits:    a.status === 'fulfilled' ? a.value : get().audits,
      reports:   r.status === 'fulfilled' ? r.value : get().reports,
      loading:   false,
      loaded:    true,
    })
  },

  addPipeline:   (p)  => set(s => ({ pipelines: [p, ...s.pipelines] })),
  removePipeline:(id) => set(s => ({ pipelines: s.pipelines.filter(p => p.id !== id) })),

  addAudit:   (a)  => set(s => ({ audits: [a, ...s.audits] })),
  removeAudit:(id) => set(s => ({
    audits:  s.audits.filter(a => a.id !== id),
    reports: s.reports.filter(r => r.id !== id),
  })),
}))
