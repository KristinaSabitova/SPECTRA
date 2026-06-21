import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ShieldCheck, Plus, X, Trash2, AlertTriangle } from 'lucide-react'
import { useDataStore } from '@/store/data'
import { useAuthStore } from '@/store/auth'
import { auditsApi, pipelinesApi } from '@/services/api'
import type { Audit, AuditStatus, Pipeline } from '@/types'
import Badge from '@/components/common/Badge'
import Button from '@/components/common/Button'
import Spinner from '@/components/common/Spinner'
import EmptyState from '@/components/common/EmptyState'
import Alert from '@/components/common/Alert'

const STATUS_VARIANT: Record<AuditStatus, string> = {
  pending:   'queued',
  running:   'running',
  completed: 'completed',
  failed:    'failed',
}

// ── Delete confirmation modal ─────────────────────────────────────────

interface DeleteConfirmProps {
  audit: Audit
  onClose: () => void
  onDeleted: (id: string) => void
}

function DeleteConfirmModal({ audit, onClose, onDeleted }: DeleteConfirmProps) {
  const { t }  = useTranslation()
  const [deleting, setDeleting] = useState(false)
  const [error, setError]       = useState('')

  async function confirm() {
    setDeleting(true)
    setError('')
    try {
      await auditsApi.delete(audit.id)
      onDeleted(audit.id)
    } catch {
      setError(t('common.error'))
      setDeleting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box modal-box--sm" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{t('audits.deleteConfirm.title')}</h2>
          <button className="modal-close" onClick={onClose} disabled={deleting}><X size={16} /></button>
        </div>
        <div className="modal-body">
          {error && <Alert type="error" message={error} />}
          <div className="delete-confirm-body">
            <div className="delete-confirm-icon"><AlertTriangle size={22} /></div>
            <div>
              <p className="delete-confirm-message">{t('audits.deleteConfirm.message')}</p>
              {audit.name && <p className="delete-confirm-name">{audit.name}</p>}
            </div>
          </div>
        </div>
        <div className="modal-footer">
          <Button variant="secondary" onClick={onClose} disabled={deleting}>
            {t('audits.deleteConfirm.cancel')}
          </Button>
          <Button variant="danger" onClick={confirm} loading={deleting}>
            <Trash2 size={13} />
            {deleting ? t('audits.deleteConfirm.deleting') : t('audits.deleteConfirm.confirm')}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── New Audit Modal ───────────────────────────────────────────────────

interface NewAuditModalProps {
  onClose: () => void
  onCreated: (audit: Audit) => void
}

function NewAuditModal({ onClose, onCreated }: NewAuditModalProps) {
  const { t } = useTranslation()
  const storePipelines               = useDataStore(s => s.pipelines)
  const [pipelines, setPipelines]    = useState<Pipeline[]>(storePipelines)
  const [pipelineId, setPipelineId]  = useState(storePipelines[0]?.id ?? '')
  const [name, setName]              = useState('')
  const [loading, setLoading]        = useState(false)
  const [fetching, setFetching]      = useState(storePipelines.length === 0)
  const [error, setError]            = useState('')

  useEffect(() => {
    if (storePipelines.length > 0) return
    pipelinesApi.list()
      .then(res => {
        setPipelines(res.data)
        if (res.data.length > 0) setPipelineId(res.data[0].id)
      })
      .catch(() => {})
      .finally(() => setFetching(false))
  }, [storePipelines.length])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!pipelineId) { setError(t('audits.modal.errors.pipelineRequired')); return }
    setLoading(true)
    setError('')
    try {
      const res = await auditsApi.create({ pipeline_id: pipelineId, name: name || undefined })
      onCreated(res.data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? t('common.error'))
      setLoading(false)
    }
  }

  const pipelineList = pipelines.length > 0 ? pipelines : storePipelines

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{t('audits.modal.title')}</h2>
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>
        <form onSubmit={submit} className="modal-body">
          {error && <Alert type="error" message={error} />}
          <div className="form-group">
            <label className="form-label">{t('audits.modal.pipeline')}</label>
            {fetching ? <Spinner /> : pipelineList.length === 0 ? (
              <p className="form-hint">{t('audits.modal.noPipelines')}</p>
            ) : (
              <select className="form-input" value={pipelineId} onChange={e => setPipelineId(e.target.value)}>
                {pipelineList.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            )}
          </div>
          <div className="form-group">
            <label className="form-label">{t('audits.modal.name')}</label>
            <input className="form-input" type="text" placeholder={t('audits.modal.namePlaceholder')}
              value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div className="modal-footer">
            <Button type="button" variant="secondary" onClick={onClose}>{t('common.cancel')}</Button>
            <Button type="submit" loading={loading} disabled={fetching || pipelineList.length === 0}>
              {loading ? t('audits.modal.submitting') : t('audits.modal.submit')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────

export default function Audits() {
  const { t }    = useTranslation()
  const audits   = useDataStore(s => s.audits)
  const loading  = useDataStore(s => s.loading)
  const loaded   = useDataStore(s => s.loaded)
  const addAudit    = useDataStore(s => s.addAudit)
  const removeAudit = useDataStore(s => s.removeAudit)

  const role      = useAuthStore(s => s.user?.role)
  const canCreate = role === 'admin' || role === 'senior' || role === 'trial'
  const canDelete = role === 'admin'

  const [showModal, setShowModal] = useState(false)
  const [toDelete, setToDelete]   = useState<Audit | null>(null)

  function handleCreated(audit: Audit) {
    setShowModal(false)
    addAudit(audit)
  }

  function handleDeleted(id: string) {
    setToDelete(null)
    removeAudit(id)
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{t('audits.title')}</h1>
          <p className="page-subtitle">{t('audits.subtitle')}</p>
        </div>
        {canCreate && (
          <Button onClick={() => setShowModal(true)}>
            <Plus size={15} />
            {t('audits.new')}
          </Button>
        )}
      </div>

      {!loaded && loading && <Spinner page />}

      {loaded && audits.length === 0 && (
        <EmptyState
          icon={ShieldCheck}
          title={t('audits.empty')}
          description={t('audits.emptyDesc')}
          action={canCreate ? (
            <Button size="sm" onClick={() => setShowModal(true)}>
              <Plus size={14} />
              {t('audits.new')}
            </Button>
          ) : undefined}
        />
      )}

      {loaded && audits.length > 0 && (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>{t('audits.columns.name')}</th>
                <th>{t('audits.columns.pipeline')}</th>
                <th>{t('audits.columns.status')}</th>
                <th>{t('audits.columns.findings')}</th>
                <th>{t('audits.columns.created')}</th>
                <th>{t('audits.columns.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {audits.map(audit => (
                <tr key={audit.id}>
                  <td style={{ fontWeight: 500 }}>
                    {audit.name ?? <span className="text-muted">—</span>}
                  </td>
                  <td>{audit.pipeline_name}</td>
                  <td>
                    <Badge
                      variant={STATUS_VARIANT[audit.status] as 'queued' | 'running' | 'completed' | 'failed'}
                      label={t(`audits.status.${audit.status}`)}
                    />
                  </td>
                  <td style={{ fontWeight: 600 }}>{audit.findings_count}</td>
                  <td className="mono" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {new Date(audit.created_at).toLocaleString()}
                  </td>
                  <td>
                    <div className="row-actions">
                      <Link to={`/audits/${audit.id}`} className="btn btn-ghost btn-sm">
                        {t('common.view')}
                      </Link>
                      {canDelete && (
                        <button
                          className="btn btn-ghost-danger btn-sm"
                          onClick={() => setToDelete(audit)}
                          title={t('audits.deleteConfirm.title')}
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <NewAuditModal onClose={() => setShowModal(false)} onCreated={handleCreated} />
      )}

      {toDelete && (
        <DeleteConfirmModal
          audit={toDelete}
          onClose={() => setToDelete(null)}
          onDeleted={handleDeleted}
        />
      )}
    </div>
  )
}
