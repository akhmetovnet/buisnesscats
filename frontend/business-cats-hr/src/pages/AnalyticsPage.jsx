import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'

export default function AnalyticsPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await api.analytics(sessionId)
      setData(res)
    } catch (err) {
      setError(err.message || 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [sessionId])

  return (
    <div className="page">
      <div className="page-header">
        <h1>Analytics</h1>
        <div className="actions">
          <button className="btn btn-secondary" onClick={() => navigate(`/session/${sessionId}`)}>
            Back to session
          </button>
          <button className="btn btn-secondary" onClick={load}>
            Recompute
          </button>
          <a
            className="btn"
            href={api.reportUrl(sessionId)}
            target="_blank"
            rel="noreferrer"
          >
            Download PDF
          </a>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="muted">Loading analytics...</div>
      ) : (
        <>
          <div className="card">
            <div className="card-title">Overall: {data?.overall ?? '—'}</div>
            <div className="muted">Session ID: {data?.sessionId}</div>
          </div>

          <div className="card">
            <div className="section-title">Competencies</div>
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Score</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {(data?.competencies || []).map((c, idx) => (
                  <tr key={idx}>
                    <td>
                      <div style={{ fontWeight: 700 }}>{c.name}</div>
                      <div className="muted">{c.explanation}</div>
                    </td>
                    <td>{c.score}</td>
                    <td>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                        {JSON.stringify(c.evidence, null, 2)}
                      </pre>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <div className="section-title">Recommendations</div>
            {data?.recommendations?.length ? (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {data.recommendations.map((r, i) => (
                  <li key={i} style={{ marginBottom: 6 }}>
                    {r}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="muted">No recommendations yet.</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
