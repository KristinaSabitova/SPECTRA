import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  GitBranch,
  ShieldCheck,
  FileText,
  LogOut,
  Users,
  ScanSearch,
  type LucideIcon,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/services/api'
import type { UserRole } from '@/types'

interface NavItem {
  to: string
  icon: LucideIcon
  key: string
  roles?: UserRole[]
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard',    icon: LayoutDashboard, key: 'nav.dashboard' },
  { to: '/pipelines',    icon: GitBranch,       key: 'nav.pipelines',   roles: ['admin', 'senior', 'trial'] },
  { to: '/audits',       icon: ShieldCheck,     key: 'nav.audits'    },
  { to: '/reports',      icon: FileText,        key: 'nav.reports'   },
  { to: '/config-audit', icon: ScanSearch,      key: 'nav.configAudit', roles: ['admin', 'senior'] },
  { to: '/users',        icon: Users,           key: 'nav.users',       roles: ['admin'] },
]

export default function Sidebar() {
  const { t } = useTranslation()
  const { user, clearAuth } = useAuthStore()
  const role = user?.role as UserRole | undefined

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || (role && item.roles.includes(role))
  )

  function handleLogout() {
    authApi.logout().catch(() => {})
    clearAuth()
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-name">SPECTRA</span>
        <span className="sidebar-brand-tagline">{t('app.tagline')}</span>
      </div>

      <nav className="sidebar-section">
        <p className="sidebar-section-label">{t('nav.main')}</p>
        {visibleItems.map(({ to, icon: Icon, key }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
          >
            <Icon />
            {t(key)}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="sidebar-logout" onClick={handleLogout}>
          <LogOut />
          {t('topbar.logout')}
        </button>
      </div>
    </aside>
  )
}
