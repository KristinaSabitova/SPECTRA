import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Suspense, useEffect, useState, type ReactNode } from 'react'
import { useAuthStore } from '@/store/auth'
import { authApi, setupApi } from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import Spinner from '@/components/common/Spinner'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import ForgotPassword from '@/pages/ForgotPassword'
import Setup from '@/pages/Setup'
import Dashboard from '@/pages/Dashboard'
import Pipelines from '@/pages/Pipelines'
import Audits from '@/pages/Audits'
import Reports from '@/pages/Reports'
import RunDetail from '@/pages/RunDetail'
import Profile from '@/pages/Profile'
import Users from '@/pages/Users'
import ConfigAudit from '@/pages/ConfigAudit'
import ForceChangePassword from '@/pages/ForceChangePassword'
import Scan from '@/pages/Scan'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const mustChangePassword = useAuthStore((s) => s.mustChangePassword)
  const location = useLocation()

  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (mustChangePassword && !location.pathname.includes('force-change-password')) {
    return <Navigate to="/force-change-password" replace />
  }
  return <>{children}</>
}

function AdminRoute({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user || user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function SeniorPlusRoute({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user || user.role === 'junior') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  const [setupChecked, setSetupChecked] = useState(false)
  const [needsSetup, setNeedsSetup] = useState(false)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)
  const updateUser = useAuthStore((s) => s.updateUser)

  useEffect(() => {
    setupApi.status()
      .then(({ data }) => {
        setNeedsSetup(data.needs_setup)
        setSetupChecked(true)
      })
      .catch(() => setSetupChecked(true))
  }, [])

  // Re-fetch user profile on load so role is never read from localStorage
  useEffect(() => {
    if (isAuthenticated && !user) {
      authApi.me()
        .then(({ data }) => updateUser(data))
        .catch(() => useAuthStore.getState().clearAuth())
    }
  }, [isAuthenticated, user, updateUser])

  if (!setupChecked) return <Spinner page />

  if (needsSetup) {
    return <Setup onDone={() => setNeedsSetup(false)} />
  }

  return (
    <Suspense fallback={<Spinner page />}>
      <Routes>
        {/* Public routes — no auth required */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/scan" element={<Scan />} />

        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Routes>
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="dashboard"             element={<Dashboard />} />
                  <Route path="pipelines"             element={<SeniorPlusRoute><Pipelines /></SeniorPlusRoute>} />
                  <Route path="audits"                element={<Audits />} />
                  <Route path="audits/:id"            element={<RunDetail />} />
                  <Route path="reports"               element={<Reports />} />
                  <Route path="profile"               element={<Profile />} />
                  <Route path="force-change-password" element={<ForceChangePassword />} />
                  <Route path="config-audit"          element={<SeniorPlusRoute><ConfigAudit /></SeniorPlusRoute>} />
                  <Route path="users"                 element={<AdminRoute><Users /></AdminRoute>} />
                </Routes>
              </AppLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  )
}
