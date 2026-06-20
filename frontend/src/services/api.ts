import axios from 'axios'
import type {
  LoginResponse, TokenResponse, RunResponse, EngineEvent,
  CreateRunRequest, Pipeline, Audit, ReportListItem,
  UserResponse, TOTPSetupResponse, CreateUserResponse, UserRole,
  ConfigScanResponse,
} from '@/types'
import { useAuthStore } from '@/store/auth'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let _refreshing: Promise<string> | null = null

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry && !window.location.pathname.startsWith('/login')) {
      original._retry = true
      try {
        if (!_refreshing) {
          _refreshing = api.post<TokenResponse>('/auth/refresh')
            .then(({ data }) => {
              useAuthStore.setState({ accessToken: data.access_token })
              return data.access_token
            })
            .finally(() => { _refreshing = null })
        }
        const token = await _refreshing
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      } catch {
        useAuthStore.getState().clearAuth()
        window.location.replace('/login')
      }
    }
    return Promise.reject(error)
  }
)

function getToken(): string {
  return useAuthStore.getState().accessToken ?? ''
}

export const setupApi = {
  status: () => api.get<{ needs_setup: boolean }>('/auth/setup-status'),
  createAdmin: (body: { email: string; username: string; password: string }) =>
    api.post<UserResponse>('/auth/setup/admin', body),
}

export const authApi = {
  login: (body: { email: string; password: string }) =>
    api.post<LoginResponse>('/auth/login', body),
  verify2fa: (body: { temp_token: string; code: string }) =>
    api.post<LoginResponse>('/auth/login/2fa', body),
  refresh: () =>
    api.post<TokenResponse>('/auth/refresh'),
  logout: () => api.post('/auth/logout'),
  logoutAll: () => api.post('/auth/logout/all'),
  me: () => api.get<UserResponse>('/auth/me'),
  changePassword: (body: { current_password: string; new_password: string }) =>
    api.put('/auth/me/password', body),
  setup2fa: () => api.post<TOTPSetupResponse>('/auth/2fa/setup'),
  enable2fa: (body: { code: string; backup_codes: string[] }) =>
    api.post('/auth/2fa/enable', body),
  disable2fa: (body: { code: string }) => api.delete('/auth/2fa', { data: body }),
}

export const usersApi = {
  list: () => api.get<UserResponse[]>('/users/'),
  create: (body: { email: string; username: string; role: UserRole }) =>
    api.post<CreateUserResponse>('/users/', body),
  toggleStatus: (id: string) => api.patch<UserResponse>(`/users/${id}/status`),
  delete: (id: string) => api.delete(`/users/${id}`),
}

export const pipelinesApi = {
  list:   () => api.get<Pipeline[]>('/pipelines/'),
  get:    (id: string) => api.get<Pipeline>(`/pipelines/${id}`),
  create: (data: { name: string; endpoint_url: string; framework: string; description?: string }) =>
    api.post<Pipeline>('/pipelines/', data),
  delete: (id: string) => api.delete(`/pipelines/${id}`),
}

export const auditsApi = {
  list:   () => api.get<Audit[]>('/audits/'),
  get:    (id: string) => api.get<Audit>(`/audits/${id}`),
  create: (data: { pipeline_id: string; name?: string }) => api.post<Audit>('/audits/', data),
  delete: (id: string) => api.delete(`/audits/${id}`),
}

export const reportsApi = {
  list: () => api.get<ReportListItem[]>('/reports/'),
  get:  (id: string) => api.get<ReportListItem>(`/reports/${id}`),
}

export const engineApi = {
  createRun: (body: CreateRunRequest) =>
    api.post<RunResponse>('/engine/runs', body),

  listRuns: (limit = 50, offset = 0) =>
    api.get<{ runs: RunResponse[]; total: number }>('/engine/runs', { params: { limit, offset } }),

  getRun: (id: string) =>
    api.get<RunResponse>(`/engine/runs/${id}`),

  getEvents: (id: string, limit = 500) =>
    api.get<EngineEvent[]>(`/engine/runs/${id}/events`, { params: { limit } }),

  cancelRun: (id: string) =>
    api.post<RunResponse>(`/engine/runs/${id}/cancel`),

  streamEvents(runId: string, onEvent: (e: EngineEvent) => void, onDone: () => void): () => void {
    const token = getToken()
    const url = `${BASE_URL}/engine/runs/${runId}/events/stream`
    let stopped = false
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null

    const run = async () => {
      try {
        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.body) { onDone(); return }
        reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''

        while (!stopped) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const lines = buf.split('\n')
          buf = lines.pop() ?? ''
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                onEvent(data as EngineEvent)
              } catch { /* malformed */ }
            } else if (line.startsWith('event: done')) {
              onDone()
              stopped = true
            }
          }
        }
      } catch { /* connection closed */ }
      if (!stopped) onDone()
    }

    run()
    return () => {
      stopped = true
      reader?.cancel()
    }
  },

  downloadReport: (runId: string, format: 'markdown' | 'pdf' | 'html') => {
    const token = getToken()
    return fetch(`${BASE_URL}/engine/runs/${runId}/report?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  },
}

export const publicApi = {
  configScan: (system_prompt: string) =>
    api.post<ConfigScanResponse>('/public/config-scan', { system_prompt }),
}
