import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import SessionsPage from './pages/SessionsPage.jsx'
import SessionPage from './pages/SessionPage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import PlayMapPage from './pages/PlayMapPage.jsx'
import './App.css'

export default function App() {
  const location = useLocation()
  const isPlay = location.pathname.startsWith('/play')

  const routes = (
    <Routes>
      <Route path="/" element={<Navigate to="/sessions" replace />} />
      <Route path="/sessions" element={<SessionsPage />} />
      <Route path="/session/:sessionId" element={<SessionPage />} />
      <Route path="/analytics/:sessionId" element={<AnalyticsPage />} />
      <Route path="/play/:sessionId/:seasonNumber" element={<PlayMapPage />} />
      <Route path="*" element={<Navigate to="/sessions" replace />} />
    </Routes>
  )

  if (isPlay) {
    return routes
  }

  return (
    <div className="app">
      <nav className="nav">
        <div className="brand">Business Cats HR</div>
        <div className="nav-links">
          <Link to="/sessions">Sessions</Link>
        </div>
      </nav>

      {routes}
    </div>
  )
}
