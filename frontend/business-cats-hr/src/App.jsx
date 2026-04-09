import { useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api.js'
import PlatformLayout from './components/PlatformLayout.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import CompetenciesPage from './pages/CompetenciesPage.jsx'
import FaqPage from './pages/FaqPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import PlayMapPage from './pages/PlayMapPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import ResetPasswordPage from './pages/ResetPasswordPage.jsx'
import SessionPage from './pages/SessionPage.jsx'
import SessionsHistoryPage from './pages/SessionsHistoryPage.jsx'
import VerifyEmailPage from './pages/VerifyEmailPage.jsx'

function RequireAuth({ authLoading, me, children }) {
  if (authLoading) return <div style={{ padding: 24 }}>Loading...</div>
  if (!me) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const navigate = useNavigate()
  const [authLoading, setAuthLoading] = useState(true)
  const [me, setMe] = useState(null)

  const refreshMe = useCallback(async () => {
    try {
      const user = await api.me()
      setMe(user)
      return user
    } catch (err) {
      if (Number(err?.status) === 401) {
        try {
          await api.authRefresh()
          const user = await api.me()
          setMe(user)
          return user
        } catch {
          setMe(null)
          return null
        }
      }
      setMe(null)
      return null
    }
  }, [])

  useEffect(() => {
    let canceled = false
    const run = async () => {
      setAuthLoading(true)
      const user = await refreshMe()
      if (!canceled) {
        setMe(user)
        setAuthLoading(false)
      }
    }
    run()
    return () => {
      canceled = true
    }
  }, [refreshMe])

  const handleLogout = async () => {
    try {
      await api.authLogout()
    } catch {
      // no-op
    }
    setMe(null)
    navigate('/login', { replace: true })
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to={me ? '/competencies' : '/login'} replace />} />
      <Route path="/login" element={me ? <Navigate to="/competencies" replace /> : <LoginPage onAuthenticated={refreshMe} />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route
        path="/play/:sessionId/:seasonNumber"
        element={
          <RequireAuth authLoading={authLoading} me={me}>
            <PlayMapPage me={me} />
          </RequireAuth>
        }
      />

      <Route
        element={
          <RequireAuth authLoading={authLoading} me={me}>
            <PlatformLayout me={me} onLogout={handleLogout} />
          </RequireAuth>
        }
      >
        <Route path="/competencies" element={<CompetenciesPage />} />
        <Route path="/profile" element={<ProfilePage me={me} onMeUpdated={refreshMe} />} />
        <Route path="/sessions/history" element={<SessionsHistoryPage />} />
        <Route path="/faq" element={<FaqPage />} />

        <Route path="/sessions" element={<Navigate to="/sessions/history" replace />} />
        <Route path="/session/:sessionId" element={<SessionPage />} />
        <Route path="/analytics/:sessionId" element={<AnalyticsPage />} />
      </Route>

      <Route path="*" element={<Navigate to={me ? '/competencies' : '/login'} replace />} />
    </Routes>
  )
}
