import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { UserPlus, Trash2, ToggleLeft, ToggleRight, X, AlertTriangle, Copy, Check } from 'lucide-react'
import { usersApi } from '@/services/api'
import type { UserResponse, UserRole } from '@/types'
import Alert from '@/components/common/Alert'
import Button from '@/components/common/Button'
import Badge from '@/components/common/Badge'
import Spinner from '@/components/common/Spinner'

export default function Users() {
  const { t } = useTranslation()
  const [users, setUsers] = useState<UserResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create modal
  const [showCreate, setShowCreate] = useState(false)
  const [createUsername, setCreateUsername] = useState('')
  const [createEmail, setCreateEmail] = useState('')
  const [createRole, setCreateRole] = useState<UserRole>('junior')
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Temp password modal
  const [tempPassword, setTempPassword] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<UserResponse | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const fetchUsers = useCallback(async () => {
    try {
      const { data } = await usersApi.list()
      setUsers(data)
    } catch {
      setError(t('common.error'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreateError(null)
    setCreateLoading(true)
    try {
      const { data } = await usersApi.create({ email: createEmail, username: createUsername, role: createRole })
      setUsers((prev) => [...prev, data.user])
      setTempPassword(data.temp_password)
      setShowCreate(false)
      setCreateUsername('')
      setCreateEmail('')
      setCreateRole('junior')
    } catch (err: unknown) {
      const res = (err as { response?: { status?: number; data?: { detail?: unknown } } }).response
      if (res?.status === 409) {
        setCreateError(t('users.errors.duplicateUser'))
      } else if (res?.status === 422) {
        const detail = res.data?.detail
        if (Array.isArray(detail) && detail.length > 0) {
          const raw = (detail[0] as { msg?: string }).msg ?? t('common.error')
          setCreateError(raw.replace(/^Value error,\s*/i, ''))
        } else {
          setCreateError(t('common.error'))
        }
      } else {
        setCreateError(t('common.error'))
      }
    } finally {
      setCreateLoading(false)
    }
  }

  async function handleToggleStatus(user: UserResponse) {
    try {
      const { data } = await usersApi.toggleStatus(user.id)
      setUsers((prev) => prev.map((u) => (u.id === data.id ? data : u)))
    } catch {
      setError(t('common.error'))
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleteLoading(true)
    try {
      await usersApi.delete(deleteTarget.id)
      setUsers((prev) => prev.filter((u) => u.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch {
      setError(t('common.error'))
    } finally {
      setDeleteLoading(false)
    }
  }

  function copyTempPassword() {
    if (!tempPassword) return
    navigator.clipboard.writeText(tempPassword)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString()
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{t('users.title')}</h1>
          <p className="page-subtitle">{t('users.subtitle')}</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setShowCreate(true); setCreateError(null) }}>
          <UserPlus size={15} />
          {t('users.new')}
        </button>
      </div>

      {error && <div style={{ marginBottom: 16 }}><Alert type="error" message={error} /></div>}

      {loading
        ? <Spinner page />
        : users.length === 0
          ? (
            <div className="empty-state">
              <p className="empty-state-title">{t('users.empty')}</p>
              <p className="empty-state-desc">{t('users.emptyDesc')}</p>
            </div>
          )
          : (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('users.columns.user')}</th>
                    <th>{t('users.columns.email')}</th>
                    <th>{t('users.columns.role')}</th>
                    <th>{t('users.columns.status')}</th>
                    <th>{t('users.columns.created')}</th>
                    <th>{t('users.columns.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td style={{ fontWeight: 500 }}>{u.username}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{u.email}</td>
                      <td><Badge variant={u.role} label={t(`common.role.${u.role}`)} /></td>
                      <td>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: 5,
                          fontSize: 12, fontWeight: 600,
                          color: u.is_active ? 'var(--success)' : 'var(--text-muted)',
                        }}>
                          <span style={{
                            width: 6, height: 6, borderRadius: '50%',
                            background: u.is_active ? 'var(--success)' : 'var(--border-strong)',
                          }} />
                          {u.is_active ? t('users.status.active') : t('users.status.inactive')}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{formatDate(u.created_at)}</td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleToggleStatus(u)}
                            title={u.is_active ? t('users.actions.deactivate') : t('users.actions.activate')}
                          >
                            {u.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                            {u.is_active ? t('users.actions.deactivate') : t('users.actions.activate')}
                          </button>
                          <button
                            className="btn btn-sm btn-ghost-danger"
                            onClick={() => setDeleteTarget(u)}
                            title={t('users.actions.delete')}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
      }

      {/* ── Create user modal ─────────────────────────────────────────── */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{t('users.modal.title')}</span>
              <button className="modal-close" onClick={() => setShowCreate(false)}><X size={16} /></button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body">
                {createError && <Alert type="error" message={createError} />}
                <div className="form-group">
                  <label className="form-label">{t('users.modal.username')}</label>
                  <input
                    type="text"
                    className="form-input"
                    value={createUsername}
                    onChange={(e) => setCreateUsername(e.target.value)}
                    placeholder={t('users.modal.usernamePlaceholder')}
                    required
                    autoFocus
                  />
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                    {t('users.modal.usernameHint')}
                  </p>
                </div>
                <div className="form-group">
                  <label className="form-label">{t('users.modal.email')}</label>
                  <input
                    type="email"
                    className="form-input"
                    value={createEmail}
                    onChange={(e) => setCreateEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">{t('users.modal.role')}</label>
                  <select
                    className="form-input"
                    value={createRole}
                    onChange={(e) => setCreateRole(e.target.value as UserRole)}
                  >
                    <option value="junior">{t('common.role.junior')}</option>
                    <option value="senior">{t('common.role.senior')}</option>
                    <option value="admin">{t('common.role.admin')}</option>
                  </select>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>
                  {t('common.cancel')}
                </button>
                <Button type="submit" loading={createLoading}>
                  {createLoading ? t('users.modal.submitting') : t('users.modal.submit')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Temp password modal ───────────────────────────────────────── */}
      {tempPassword && (
        <div className="modal-overlay">
          <div className="modal-box modal-box--sm">
            <div className="modal-header">
              <span className="modal-title">{t('users.tempPassword.title')}</span>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.6 }}>
                {t('users.tempPassword.desc')}
              </p>
              <div className="form-group">
                <label className="form-label">{t('users.tempPassword.password')}</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <code style={{
                    flex: 1, padding: '9px 12px', background: 'var(--bg)',
                    border: '1px solid var(--border)', borderRadius: 'var(--r-md)',
                    fontFamily: 'var(--mono)', fontSize: 15, letterSpacing: 1,
                    color: 'var(--text)',
                  }}>
                    {tempPassword}
                  </code>
                  <button className="btn btn-secondary" onClick={copyTempPassword}>
                    {copied ? <Check size={15} /> : <Copy size={15} />}
                  </button>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <Button onClick={() => { setTempPassword(null); setCopied(false) }}>
                {t('users.tempPassword.done')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete confirm modal ──────────────────────────────────────── */}
      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal-box modal-box--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{t('users.deleteConfirm.title')}</span>
              <button className="modal-close" onClick={() => setDeleteTarget(null)}><X size={16} /></button>
            </div>
            <div className="modal-body">
              <div className="delete-confirm-body">
                <div className="delete-confirm-icon"><AlertTriangle size={20} /></div>
                <div>
                  <p className="delete-confirm-message">{t('users.deleteConfirm.message')}</p>
                  <p className="delete-confirm-name">{deleteTarget.username} — {deleteTarget.email}</p>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setDeleteTarget(null)}>
                {t('users.deleteConfirm.cancel')}
              </button>
              <Button variant="danger" loading={deleteLoading} onClick={handleDelete}>
                {deleteLoading ? t('users.deleteConfirm.deleting') : t('users.deleteConfirm.confirm')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
