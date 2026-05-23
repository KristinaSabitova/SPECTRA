import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertTriangle } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/services/api'
import Alert from '@/components/common/Alert'
import Button from '@/components/common/Button'

export default function ForceChangePassword() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setMustChangePassword = useAuthStore((s) => s.setMustChangePassword)

  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (newPw !== confirmPw) {
      setError(t('forceChange.passwordMismatch'))
      return
    }
    setLoading(true)
    try {
      await authApi.changePassword({ current_password: currentPw, new_password: newPw })
      setMustChangePassword(false)
      navigate('/dashboard', { replace: true })
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status
      if (status === 401) {
        setError(t('auth.errors.invalidCredentials'))
      } else {
        setError(t('forceChange.passwordHint'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 480, margin: '40px auto' }}>
      <div
        className="alert alert-warning"
        style={{ marginBottom: 24, borderRadius: 'var(--r-lg)' }}
      >
        <AlertTriangle size={18} />
        <div>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>{t('forceChange.title')}</p>
          <p style={{ fontSize: 13 }}>{t('forceChange.subtitle')}</p>
        </div>
      </div>

      <div className="card">
        {error && <div style={{ marginBottom: 16 }}><Alert type="error" message={error} /></div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="form-group">
            <label className="form-label">{t('forceChange.currentPassword')}</label>
            <input
              type="password"
              className="form-input"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              required
              autoFocus
              autoComplete="current-password"
            />
          </div>

          <div className="form-group">
            <label className="form-label">{t('forceChange.newPassword')}</label>
            <input
              type="password"
              className="form-input"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              required
              autoComplete="new-password"
            />
            <p className="form-hint">{t('forceChange.passwordHint')}</p>
          </div>

          <div className="form-group">
            <label className="form-label">{t('forceChange.confirmPassword')}</label>
            <input
              type="password"
              className="form-input"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>

          <Button type="submit" loading={loading} fullWidth size="lg">
            {loading ? t('forceChange.submitting') : t('forceChange.submit')}
          </Button>
        </form>
      </div>
    </div>
  )
}
