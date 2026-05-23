import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/services/api'
import LanguageSelector from '@/components/layout/LanguageSelector'
import Alert from '@/components/common/Alert'
import Button from '@/components/common/Button'

type Step = 'credentials' | 'totp'

function errorKey(status?: number): string {
  if (status === 401) return 'auth.errors.invalidCredentials'
  if (status === 403) return 'auth.errors.accountDisabled'
  return 'auth.errors.networkError'
}

export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const setMustChangePassword = useAuthStore((s) => s.setMustChangePassword)

  const [step, setStep] = useState<Step>('credentials')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tempToken, setTempToken] = useState('')
  const [code, setCode] = useState('')
  const [useBackup, setUseBackup] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { data } = await authApi.login({ email, password })
      if (data.requires_2fa && data.temp_token) {
        setTempToken(data.temp_token)
        setStep('totp')
      } else if (data.tokens && data.user) {
        setAuth(data.user, data.tokens)
        if (data.must_change_password) {
          setMustChangePassword(true)
          navigate('/force-change-password', { replace: true })
        } else {
          navigate('/dashboard', { replace: true })
        }
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status
      setError(t(errorKey(status)))
    } finally {
      setLoading(false)
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { data } = await authApi.verify2fa({ temp_token: tempToken, code })
      if (data.tokens && data.user) {
        setAuth(data.user, data.tokens)
        navigate('/dashboard', { replace: true })
      }
    } catch {
      setError(t('auth.errors.invalidCode'))
    } finally {
      setLoading(false)
    }
  }

  function switchBackup() {
    setUseBackup((v) => !v)
    setCode('')
    setError(null)
  }

  function backToCredentials() {
    setStep('credentials')
    setCode('')
    setTempToken('')
    setError(null)
  }

  return (
    <div className="login-page">
      <div className="login-card">

        {/* Header */}
        <div className="login-header">
          <span className="login-logo">SPECTRA</span>
          <p className="login-tagline">{t('app.tagline')}</p>
        </div>

        {error && <div style={{ marginBottom: 16 }}><Alert type="error" message={error} /></div>}

        {/* ── Paso 1: credenciales ── */}
        {step === 'credentials' && (
          <form onSubmit={handleLogin} className="login-form">
            <div className="form-group">
              <label className="form-label" htmlFor="email">{t('auth.email')}</label>
              <input
                id="email"
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.emailPlaceholder')}
                required
                autoComplete="email"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">{t('auth.password')}</label>
              <input
                id="password"
                type="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.passwordPlaceholder')}
                required
                autoComplete="current-password"
              />
            </div>

            <Button type="submit" loading={loading} fullWidth size="lg">
              {loading ? t('auth.loggingIn') : t('auth.loginButton')}
            </Button>
          </form>
        )}

        {/* ── Paso 2: TOTP ── */}
        {step === 'totp' && (
          <form onSubmit={handleVerify} className="login-form">
            <div className="totp-header">
              <p className="totp-title">{t('auth.totp.title')}</p>
              <p className="totp-desc">{t('auth.totp.desc')}</p>
            </div>

            <div className="form-group">
              <label className="form-label">
                {useBackup ? t('auth.totp.backupCode') : t('auth.totp.code')}
              </label>
              <input
                type="text"
                className={`form-input ${!useBackup ? 'totp-input' : ''}`}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder={useBackup ? t('auth.totp.backupPlaceholder') : t('auth.totp.codePlaceholder')}
                required
                autoComplete="one-time-code"
                inputMode={useBackup ? 'text' : 'numeric'}
                maxLength={useBackup ? 9 : 6}
                autoFocus
              />
            </div>

            <button type="button" className="link-btn" onClick={switchBackup}>
              {useBackup ? t('auth.totp.code') : t('auth.totp.useBackup')}
            </button>

            <Button type="submit" loading={loading} fullWidth size="lg">
              {loading ? t('auth.totp.verifying') : t('auth.totp.verify')}
            </Button>

            <button type="button" className="link-btn" onClick={backToCredentials}>
              ← {t('auth.totp.backToLogin')}
            </button>
          </form>
        )}

        {/* Selector de idioma */}
        <div className="login-footer">
          <LanguageSelector variant="login" />
        </div>
      </div>
    </div>
  )
}
