import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Shield, ShieldCheck, ShieldOff, Copy, Check } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/services/api'
import Alert from '@/components/common/Alert'
import Button from '@/components/common/Button'
import Badge from '@/components/common/Badge'

type TotpStep = 'idle' | 'setup' | 'disable'

export default function Profile() {
  const { t } = useTranslation()
  const { user, updateUser } = useAuthStore()

  // ── Change password ──────────────────────────────────────────────────
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [pwLoading, setPwLoading] = useState(false)
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setPwError(null)
    setPwSuccess(false)
    if (newPw !== confirmPw) {
      setPwError(t('profile.passwordMismatch'))
      return
    }
    setPwLoading(true)
    try {
      await authApi.changePassword({ current_password: currentPw, new_password: newPw })
      setPwSuccess(true)
      setCurrentPw('')
      setNewPw('')
      setConfirmPw('')
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status
      if (status === 401) {
        setPwError(t('auth.errors.invalidCredentials'))
      } else {
        setPwError(t('profile.passwordHint'))
      }
    } finally {
      setPwLoading(false)
    }
  }

  // ── 2FA ──────────────────────────────────────────────────────────────
  const [totpStep, setTotpStep] = useState<TotpStep>('idle')
  const [totpSetup, setTotpSetup] = useState<{ secret: string; qr_uri: string; backup_codes: string[] } | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [totpLoading, setTotpLoading] = useState(false)
  const [totpError, setTotpError] = useState<string | null>(null)
  const [totpSuccess, setTotpSuccess] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function startSetup2FA() {
    setTotpError(null)
    setTotpLoading(true)
    try {
      const { data } = await authApi.setup2fa()
      setTotpSetup(data)
      setTotpStep('setup')
    } catch {
      setTotpError(t('common.error'))
    } finally {
      setTotpLoading(false)
    }
  }

  async function confirmEnable2FA(e: React.FormEvent) {
    e.preventDefault()
    if (!totpSetup) return
    setTotpError(null)
    setTotpLoading(true)
    try {
      await authApi.enable2fa({ code: totpCode, secret: totpSetup.secret, backup_codes: totpSetup.backup_codes })
      const { data: fresh } = await authApi.me()
      updateUser(fresh)
      setTotpStep('idle')
      setTotpSetup(null)
      setTotpCode('')
      setTotpSuccess(t('profile.2faEnabled'))
    } catch {
      setTotpError(t('auth.errors.invalidCode'))
    } finally {
      setTotpLoading(false)
    }
  }

  async function confirmDisable2FA(e: React.FormEvent) {
    e.preventDefault()
    setTotpError(null)
    setTotpLoading(true)
    try {
      await authApi.disable2fa({ code: totpCode })
      const { data: fresh } = await authApi.me()
      updateUser(fresh)
      setTotpStep('idle')
      setTotpCode('')
      setTotpSuccess(t('profile.2faDisabled'))
    } catch {
      setTotpError(t('auth.errors.invalidCode'))
    } finally {
      setTotpLoading(false)
    }
  }

  function cancelTotp() {
    setTotpStep('idle')
    setTotpSetup(null)
    setTotpCode('')
    setTotpError(null)
  }

  function copySecret() {
    if (!totpSetup) return
    navigator.clipboard.writeText(totpSetup.secret)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!user) return null

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">{t('profile.title')}</h1>
          <p className="page-subtitle">{t('profile.subtitle')}</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'start' }}>
        {/* ── Account info ─────────────────────────────────────────── */}
        <div className="section-card">
          <p className="section-card-title">{t('profile.accountInfo')}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 3 }}>
                {t('auth.email')}
              </p>
              <p style={{ fontSize: 14, color: 'var(--text)' }}>{user.email}</p>
            </div>
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 3 }}>
                {t('setup.username')}
              </p>
              <p style={{ fontSize: 14, color: 'var(--text)' }}>{user.username}</p>
            </div>
            <div>
              <p style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 6 }}>
                {t('users.columns.role')}
              </p>
              <Badge variant={user.role} label={t(`common.role.${user.role}`)} />
            </div>
          </div>
        </div>

        {/* ── Change password ───────────────────────────────────────── */}
        <div className="section-card">
          <p className="section-card-title">{t('profile.changePassword')}</p>

          {pwError && <div style={{ marginBottom: 14 }}><Alert type="error" message={pwError} /></div>}
          {pwSuccess && <div style={{ marginBottom: 14 }}><Alert type="success" message={t('profile.passwordChanged')} /></div>}

          <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">{t('profile.currentPassword')}</label>
              <input
                type="password"
                className="form-input"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            <div className="form-group">
              <label className="form-label">{t('profile.newPassword')}</label>
              <input
                type="password"
                className="form-input"
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                required
                autoComplete="new-password"
              />
              <p className="form-hint">{t('profile.passwordHint')}</p>
            </div>
            <div className="form-group">
              <label className="form-label">{t('profile.confirmPassword')}</label>
              <input
                type="password"
                className="form-input"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            <Button type="submit" loading={pwLoading} fullWidth>
              {pwLoading ? t('profile.saving') : t('common.save')}
            </Button>
          </form>
        </div>

        {/* ── 2FA ──────────────────────────────────────────────────── */}
        <div className="section-card" style={{ gridColumn: '1 / -1' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {user.totp_enabled
                ? <ShieldCheck size={20} color="var(--success)" />
                : <Shield size={20} color="var(--text-muted)" />
              }
              <div>
                <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
                  {t('profile.twoFactor')}
                </p>
                <p style={{ fontSize: 12, color: user.totp_enabled ? 'var(--success)' : 'var(--text-muted)' }}>
                  {user.totp_enabled ? t('profile.twoFactorEnabled') : t('profile.twoFactorDisabled')}
                </p>
              </div>
            </div>
            {totpStep === 'idle' && (
              user.totp_enabled
                ? <button className="btn btn-secondary btn-sm" onClick={() => { setTotpStep('disable'); setTotpError(null); setTotpSuccess(null) }}>
                    <ShieldOff size={14} /> {t('profile.disable2FA')}
                  </button>
                : <button className="btn btn-primary btn-sm" onClick={startSetup2FA} disabled={totpLoading}>
                    <Shield size={14} /> {t('profile.enable2FA')}
                  </button>
            )}
          </div>

          {totpSuccess && (
            <Alert type="success" message={totpSuccess} />
          )}

          {/* Setup flow */}
          {totpStep === 'setup' && totpSetup && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16 }}>
              <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>
                {t('profile.setup2FATitle')}
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
                {t('profile.setup2FADesc')}
              </p>

              <div style={{ marginBottom: 16 }}>
                <p className="form-label" style={{ marginBottom: 6 }}>{t('profile.secretKey')}</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <code style={{
                    flex: 1, padding: '9px 12px', background: 'var(--bg)', border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)', fontFamily: 'var(--mono)', fontSize: 14,
                    letterSpacing: 2, color: 'var(--text)',
                  }}>
                    {totpSetup.secret}
                  </code>
                  <button className="btn btn-secondary btn-sm" onClick={copySecret} style={{ flexShrink: 0 }}>
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                  </button>
                </div>
              </div>

              <div style={{ marginBottom: 20 }}>
                <p className="form-label" style={{ marginBottom: 8 }}>{t('profile.backupCodesTitle')}</p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>{t('profile.backupCodesDesc')}</p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
                  {totpSetup.backup_codes.map((code) => (
                    <code key={code} style={{
                      padding: '6px 8px', background: 'var(--bg)', border: '1px solid var(--border)',
                      borderRadius: 'var(--r-sm)', fontFamily: 'var(--mono)', fontSize: 12,
                      textAlign: 'center', color: 'var(--text-secondary)',
                    }}>
                      {code}
                    </code>
                  ))}
                </div>
              </div>

              {totpError && <div style={{ marginBottom: 12 }}><Alert type="error" message={totpError} /></div>}

              <form onSubmit={confirmEnable2FA} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">{t('profile.confirmCode')}</label>
                  <input
                    type="text"
                    className="form-input totp-input"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    placeholder="000000"
                    maxLength={6}
                    inputMode="numeric"
                    required
                    autoFocus
                  />
                </div>
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <Button type="submit" loading={totpLoading}>
                    {t('profile.confirm2FA')}
                  </Button>
                  <button type="button" className="btn btn-secondary" onClick={cancelTotp}>
                    {t('common.cancel')}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Disable flow */}
          {totpStep === 'disable' && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16 }}>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
                {t('profile.disable2FADesc')}
              </p>

              {totpError && <div style={{ marginBottom: 12 }}><Alert type="error" message={totpError} /></div>}

              <form onSubmit={confirmDisable2FA} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">{t('auth.totp.code')}</label>
                  <input
                    type="text"
                    className="form-input totp-input"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    placeholder="000000"
                    maxLength={6}
                    inputMode="numeric"
                    required
                    autoFocus
                  />
                </div>
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <Button type="submit" variant="danger" loading={totpLoading}>
                    {t('profile.disable2FA')}
                  </Button>
                  <button type="button" className="btn btn-secondary" onClick={cancelTotp}>
                    {t('common.cancel')}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
