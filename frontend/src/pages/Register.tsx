import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import Alert from '@/components/common/Alert'
import Button from '@/components/common/Button'
import LanguageSelector from '@/components/layout/LanguageSelector'

export default function Register() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await api.post('/auth/register', {
        email,
        username,
        password,
        invite_code: inviteCode,
      })
      navigate('/login', { replace: true, state: { registered: true } })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      if (detail === 'Código de invitación inválido') {
        setError('Código de invitación inválido.')
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError('No se pudo completar el registro. Inténtalo de nuevo.')
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
          <p className="login-tagline">Crear cuenta</p>
        </div>

        {error && <div style={{ marginBottom: 16 }}><Alert type="error" message={error} /></div>}

        <form onSubmit={handleRegister} className="login-form">
          <div className="form-group">
            <label className="form-label" htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@email.com"
              required
              autoComplete="email"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="username">Usuario</label>
            <input
              id="username"
              type="text"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="nombre_usuario"
              required
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Mínimo 12 caracteres"
              required
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="invite-code">Código de invitación</label>
            <input
              id="invite-code"
              type="text"
              className="form-input"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              placeholder="Código de invitación"
              required
              autoComplete="off"
            />
          </div>

          <Button type="submit" loading={loading} fullWidth size="lg">
            {loading ? 'Registrando...' : 'Crear cuenta'}
          </Button>
        </form>

        <div style={{ marginTop: 16, textAlign: 'center', fontSize: 13 }}>
          <span style={{ color: 'var(--text-muted)' }}>¿Ya tienes cuenta? </span>
          <Link to="/login" style={{ color: 'var(--primary)', textDecoration: 'none' }}>
            Inicia sesión
          </Link>
        </div>

        <div className="login-footer">
          <LanguageSelector variant="login" />
        </div>
      </div>
    </div>
  )
}
