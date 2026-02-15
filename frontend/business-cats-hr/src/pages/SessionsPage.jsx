import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, apiPost } from '../api.js'

const fmt = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString()
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [loginBusy, setLoginBusy] = useState(false)
  const navigate = useNavigate()

  const loadSessions = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await api.sessions()
      setSessions(data || [])
    } catch (err) {
      setError(err.message || 'Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSessions()
  }, [])

  const doLogin = async () => {
    try {
      setLoginBusy(true)
      const res = await apiPost('/api/demo/login', {
        role: 'candidate',
        fullName: 'Timur',
      })
      if (res?.userId) {
        localStorage.setItem('demoUserId', res.userId)
        await loadSessions()
      } else {
        setError('Demo login failed: no userId')
      }
    } catch (err) {
      setError(err.message || 'Demo login failed')
    } finally {
      setLoginBusy(false)
    }
  }

  const handleNewSession = async () => {
    try {
      setCreating(true)
      const data = await api.startSession()
      if (data?.sessionId) {
        navigate(`/session/${data.sessionId}`)
      } else {
        setError('Failed to start session')
      }
    } catch (err) {
      setError(err.message || 'Failed to start session')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Sessions</h1>
        <div className="actions">
          <button className="btn btn-secondary" onClick={doLogin} disabled={loginBusy}>
            {loginBusy ? 'Logging in...' : 'Demo login'}
          </button>
          <button className="btn" onClick={handleNewSession} disabled={creating}>
            {creating ? 'Creating...' : 'New session'}
          </button>
          <button className="btn btn-secondary" onClick={loadSessions} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {loading ? (
        <div className="muted">Loading sessions...</div>
      ) : sessions.length === 0 ? (
        <div className="muted">No sessions yet.</div>
      ) : (
        <div className="grid">
          {sessions.map((s) => (
            <div className="card" key={s.id}>
              <div className="card-title">Session {s.id.slice(0, 8)}</div>
              <div className="row">
                <span className="pill">{s.status}</span>
                <span className="pill">{s.assignedRole}</span>
              </div>
              <div className="muted" style={{ marginTop: 8 }}>
                Started: {fmt(s.startedAt)}
              </div>
              <div className="muted">Finished: {fmt(s.finishedAt)}</div>
              <div style={{ marginTop: 8 }}>
                Player: {s.resultCoinsPlayer} | Bot: {s.resultCoinsBot}
              </div>
              <div className="actions" style={{ marginTop: 12 }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => navigate(`/session/${s.id}`)}
                >
                  View
                </button>
                <button
                  className="btn btn-ghost"
                  onClick={() => navigate(`/analytics/${s.id}`)}
                >
                  Results
                </button>
                <button
                  className="btn"
                  onClick={() => navigate(`/play/${s.id}/1`)}
                >
                  Play
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
