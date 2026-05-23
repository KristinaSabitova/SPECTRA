import { useTranslation } from 'react-i18next'
import { LogOut, User } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/services/api'
import LanguageSelector from './LanguageSelector'

const PAGE_KEYS: Record<string, string> = {
  '/dashboard':             'nav.dashboard',
  '/pipelines':             'nav.pipelines',
  '/audits':                'nav.audits',
  '/reports':               'nav.reports',
  '/profile':               'nav.profile',
  '/users':                 'nav.users',
  '/config-audit':          'nav.configAudit',
  '/force-change-password': 'forceChange.title',
}

export default function Topbar() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { user, clearAuth } = useAuthStore()

  const pageKey = PAGE_KEYS[location.pathname] ?? 'app.name'

  function handleLogout() {
    authApi.logout().catch(() => {})
    clearAuth()
    navigate('/login', { replace: true })
  }

  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : '??'

  return (
    <header className="topbar">
      <span className="topbar-breadcrumb">{t(pageKey)}</span>

      <div className="topbar-right">
        <LanguageSelector variant="topbar" />

        <div className="topbar-divider" />

        <button
          className="topbar-user"
          title={t('topbar.profile')}
          onClick={() => navigate('/profile')}
        >
          <div className="topbar-avatar">{initials}</div>
          <div className="topbar-user-info">
            <span className="topbar-user-name">{user?.username ?? '—'}</span>
            <span className="topbar-user-role">
              {user ? t(`common.role.${user.role}`) : ''}
            </span>
          </div>
          <User size={13} style={{ color: 'var(--text-muted)', marginLeft: 4 }} />
        </button>

        <div className="topbar-divider" />

        <button
          className="btn btn-ghost btn-sm"
          onClick={handleLogout}
          title={t('topbar.logout')}
        >
          <LogOut size={15} />
          {t('topbar.logout')}
        </button>
      </div>
    </header>
  )
}
