import { Link } from 'react-router-dom'
import LanguageSelector from '@/components/layout/LanguageSelector'

export default function ForgotPassword() {
  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <span className="login-logo">SPECTRA</span>
          <p className="login-tagline">Recuperar contraseña</p>
        </div>

        <div style={{ textAlign: 'center', padding: '8px 0 24px' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, lineHeight: '1.6', marginBottom: 20 }}>
            El restablecimiento de contraseña no está disponible de forma automática.
            <br />
            Contacta con el administrador para recuperar el acceso a tu cuenta.
          </p>
          <Link to="/login" style={{ color: 'var(--primary)', fontSize: 14 }}>
            ← Volver al inicio de sesión
          </Link>
        </div>

        <div className="login-footer">
          <LanguageSelector variant="login" />
        </div>
      </div>
    </div>
  )
}
