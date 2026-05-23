import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { GitBranch, Plus, X, Trash2, AlertTriangle } from 'lucide-react'
import { useDataStore } from '@/store/data'
import { useAuthStore } from '@/store/auth'
import { pipelinesApi } from '@/services/api'
import type { Framework, Pipeline } from '@/types'
import Button from '@/components/common/Button'
import Spinner from '@/components/common/Spinner'
import Alert from '@/components/common/Alert'
import EmptyState from '@/components/common/EmptyState'

const FRAMEWORKS: { value: Framework; label: string }[] = [
  { value: 'langchain', label: 'LangChain' },
  { value: 'autogen',   label: 'AutoGen'   },
  { value: 'n8n',       label: 'n8n'       },
  { value: 'other',     label: 'Otro'       },
]

const FW_COLOR: Record<string, string> = {
  langchain: '#22C55E',
  autogen:   '#8B5CF6',
  n8n:       '#F97316',
  other:     '#64748B',
}

// ── Delete confirm modal ──────────────────────────────────────────────

interface DeletePipelineModalProps {
  pipeline: Pipeline
  onClose: () => void
  onDeleted: (id: string) => void
}

function DeletePipelineModal({ pipeline, onClose, onDeleted }: DeletePipelineModalProps) {
  const { t } = useTranslation()
  const [deleting, setDeleting] = useState(false)
  const [error, setError]       = useState('')

  async function confirm() {
    setDeleting(true)
    setError('')
    try {
      await pipelinesApi.delete(pipeline.id)
      onDeleted(pipeline.id)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (detail?.toLowerCase().includes('audit')) {
        setError(t('pipelines.deleteConfirm.hasAudits'))
      } else {
        setError(detail ?? t('common.error'))
      }
      setDeleting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--sm" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{t('pipelines.deleteConfirm.title')}</h2>
          <button className="modal-close" onClick={onClose} disabled={deleting}><X size={16} /></button>
        </div>
        <div className="modal-body">
          {error && <Alert type="error" message={error} />}
          <div className="delete-confirm-body">
            <div className="delete-confirm-icon">
              <AlertTriangle size={22} />
            </div>
            <div>
              <p className="delete-confirm-message">{t('pipelines.deleteConfirm.message')}</p>
              <p className="delete-confirm-name">{pipeline.name}</p>
            </div>
          </div>
        </div>
        <div className="modal-footer">
          <Button variant="secondary" onClick={onClose} disabled={deleting}>
            {t('pipelines.deleteConfirm.cancel')}
          </Button>
          <Button variant="danger" onClick={confirm} loading={deleting}>
            <Trash2 size={13} />
            {deleting ? t('pipelines.deleteConfirm.deleting') : t('pipelines.deleteConfirm.confirm')}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── New Pipeline Modal ────────────────────────────────────────────────

interface NewPipelineModalProps {
  onClose: () => void
  onCreated: (p: Pipeline) => void
}

function NewPipelineModal({ onClose, onCreated }: NewPipelineModalProps) {
  const { t } = useTranslation()
  const [name,      setName]      = useState('')
  const [url,       setUrl]       = useState('')
  const [framework, setFramework] = useState<Framework>('langchain')
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setError(t('pipelines.modal.errors.nameRequired')); return }
    if (!url.trim())  { setError(t('pipelines.modal.errors.urlRequired'));  return }
    setLoading(true)
    setError('')
    try {
      const res = await pipelinesApi.create({ name, endpoint_url: url, framework })
      onCreated(res.data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? t('common.error'))
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{t('pipelines.modal.title')}</h2>
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>
        <form onSubmit={submit} className="modal-body">
          {error && <Alert type="error" message={error} />}
          <div className="form-group">
            <label className="form-label">{t('pipelines.modal.name')}</label>
            <input className="form-input" type="text" placeholder={t('pipelines.modal.namePlaceholder')}
              value={name} onChange={e => setName(e.target.value)} autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label">{t('pipelines.modal.url')}</label>
            <input className="form-input" type="url" placeholder={t('pipelines.modal.urlPlaceholder')}
              value={url} onChange={e => setUrl(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">{t('pipelines.modal.framework')}</label>
            <select className="form-input" value={framework} onChange={e => setFramework(e.target.value as Framework)}>
              {FRAMEWORKS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
            </select>
          </div>
          <div className="modal-footer">
            <Button type="button" variant="secondary" onClick={onClose}>{t('common.cancel')}</Button>
            <Button type="submit" loading={loading}>
              {loading ? t('pipelines.modal.submitting') : t('pipelines.modal.submit')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────

export default function Pipelines() {
  const { t } = useTranslation()
  const pipelines    = useDataStore(s => s.pipelines)
  const loading      = useDataStore(s => s.loading)
  const loaded       = useDataStore(s => s.loaded)
  const addPipeline  = useDataStore(s => s.addPipeline)
  const removePipeline = useDataStore(s => s.removePipeline)

  const role      = useAuthStore(s => s.user?.role)
  const canCreate = role === 'admin' || role === 'senior'
  const canDelete = role === 'admin'

  const [showModal, setShowModal] = useState(false)
  const [toDelete, setToDelete]   = useState<Pipeline | null>(null)

  function handleCreated(p: Pipeline) {
    setShowModal(false)
    addPipeline(p)
  }

  function handleDeleted(id: string) {
    setToDelete(null)
    removePipeline(id)
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{t('pipelines.title')}</h1>
          <p className="page-subtitle">{t('pipelines.subtitle')}</p>
        </div>
        {canCreate && (
          <Button onClick={() => setShowModal(true)}>
            <Plus size={15} />
            {t('pipelines.new')}
          </Button>
        )}
      </div>

      {!loaded && loading && <Spinner page />}

      {loaded && pipelines.length === 0 && (
        <div className="table-wrapper">
          <EmptyState
            icon={GitBranch}
            title={t('pipelines.empty')}
            description={t('pipelines.emptyDesc')}
            action={canCreate ? (
              <Button size="sm" onClick={() => setShowModal(true)}>
                <Plus size={14} />
                {t('pipelines.new')}
              </Button>
            ) : undefined}
          />
        </div>
      )}

      {loaded && pipelines.length > 0 && (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>{t('pipelines.columns.name')}</th>
                <th>{t('pipelines.columns.url')}</th>
                <th>{t('pipelines.columns.framework')}</th>
                <th>{t('pipelines.columns.status')}</th>
                <th>{t('pipelines.columns.created')}</th>
                {canDelete && <th>{t('pipelines.columns.actions')}</th>}
              </tr>
            </thead>
            <tbody>
              {pipelines.map(p => (
                <tr key={p.id}>
                  <td style={{ fontWeight: 500 }}>{p.name}</td>
                  <td className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {p.endpoint_url ? trimUrl(p.endpoint_url) : '—'}
                  </td>
                  <td>
                    {p.framework
                      ? <FrameworkBadge framework={p.framework} />
                      : <span className="text-muted">—</span>}
                  </td>
                  <td>
                    <span className="badge badge-info">{t('pipelines.status.active')}</span>
                  </td>
                  <td className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {new Date(p.created_at).toLocaleDateString()}
                  </td>
                  {canDelete && (
                    <td>
                      <div className="row-actions">
                        <button
                          className="btn btn-ghost-danger btn-sm"
                          onClick={() => setToDelete(p)}
                          title={t('pipelines.deleteConfirm.title')}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <NewPipelineModal onClose={() => setShowModal(false)} onCreated={handleCreated} />
      )}

      {toDelete && (
        <DeletePipelineModal
          pipeline={toDelete}
          onClose={() => setToDelete(null)}
          onDeleted={handleDeleted}
        />
      )}
    </div>
  )
}

function FrameworkBadge({ framework }: { framework: string }) {
  const color = FW_COLOR[framework] ?? FW_COLOR.other
  const label = framework.charAt(0).toUpperCase() + framework.slice(1)
  return (
    <span className="fw-badge" style={{ '--fw-color': color } as React.CSSProperties}>
      {label}
    </span>
  )
}

function trimUrl(url: string): string {
  try {
    const u = new URL(url)
    return (u.host + u.pathname.replace(/\/$/, '')).slice(0, 38)
  } catch { return url.slice(0, 38) }
}
