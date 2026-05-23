import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { setupApi } from '@/services/api'
import LanguageSelector from '@/components/layout/LanguageSelector'
import Alert from '@/components/common/Alert'
import Button from '@/components/common/Button'

interface Props {
  onDone: () => void
}

export default function Setup({ onDone }: Props) {
  const { t } = useTranslation()

  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await setupApi.createAdmin({ email, username, password })
      setSuccess(true)
      setTimeout(onDone, 1500)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      if (typeof detail === 'string' && detail.includes('already')) {
        setError(t('setup.errors.alreadySetup'))
      } else {
        setError(t('setup.errors.weakPassword'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <span className="login-logo">SPECTRA</span>
          <p className="login-tagline">{t('app.tagline')}</p>
        </div>

        <div style={{ marginBottom: 20 }}>
          <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)', marginBottom: 6 }}>
            {t('setup.title')}
          </p>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            {t('setup.subtitle')}
          </p>
        </div>

        {error && <div style={{ marginBottom: 16 }}><Alert type="error" message={error} /></div>}
        {success && (
          <div style={{ marginBottom: 16 }}>
            <Alert type="success" message={t('setup.success')} />
          </div>
        )}

        {!success && (
          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label className="form-label" htmlFor="setup-email">{t('auth.email')}</label>
              <input
                id="setup-email"
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.emailPlaceholder')}
                required
                autoFocus
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="setup-username">{t('setup.username')}</label>
              <input
                id="setup-username"
                type="text"
                className="form-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t('setup.usernamePlaceholder')}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="setup-password">{t('auth.password')}</label>
              <input
                id="setup-password"
                type="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.passwordPlaceholder')}
                required
              />
              <p className="form-hint">{t('setup.passwordHint')}</p>
            </div>

            <Button type="submit" loading={loading} fullWidth size="lg">
              {loading ? t('setup.submitting') : t('setup.submit')}
            </Button>
          </form>
        )}

        <div className="login-footer">
          <LanguageSelector variant="login" />
        </div>
      </div>
    </div>
  )
}
