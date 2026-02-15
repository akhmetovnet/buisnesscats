import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'

const CAT_TYPES = ['black', 'white', 'ginger', 'gray']

const safeNum = (value, fallback = 0) => {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

const fmt = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString()
}

const short = (value, limit = 90) => {
  if (!value) return '—'
  const str = typeof value === 'string' ? value : JSON.stringify(value)
  if (str.length <= limit) return str
  return `${str.slice(0, limit)}…`
}

export default function SessionPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()

  const [detail, setDetail] = useState(null)
  const [seasonNumber, setSeasonNumber] = useState(1)
  const [state, setState] = useState(null)
  const [market, setMarket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [catType, setCatType] = useState('black')
  const [catSex] = useState('M')
  const [qty, setQty] = useState(1)
  const [creditAmount, setCreditAmount] = useState(5)
  const [creditType, setCreditType] = useState('consumer')
  const [busy, setBusy] = useState(false)

  const session = detail?.session
  const seasons = detail?.seasons || []
  const isFinished = session?.status === 'finished'

  const maxSeason = useMemo(() => {
    if (!seasons.length) return 1
    return Math.max(...seasons.map((s) => s.season_number))
  }, [seasons])

  const currentSeason = useMemo(() => {
    return seasons.find((s) => s.season_number === seasonNumber) || null
  }, [seasons, seasonNumber])

  const loadDetail = async (preferredSeason) => {
    try {
      setLoading(true)
      setError('')
      const data = await api.sessionDetail(sessionId)
      setDetail(data)
      const last = data?.seasons?.length
        ? Math.max(...data.seasons.map((s) => s.season_number))
        : 1
      setSeasonNumber(preferredSeason || last)
    } catch (err) {
      setError(err.message || 'Failed to load session')
    } finally {
      setLoading(false)
    }
  }

  const loadStateMarket = async (sn) => {
    try {
      setError('')
      const [st, mk] = await Promise.all([
        api.state(sessionId, sn, 'shop', 1),
        api.market(sessionId, sn, 'shop', 1),
      ])
      setState(st)
      setMarket(mk)
    } catch (err) {
      setError(err.message || 'Failed to load state/market')
    }
  }

  useEffect(() => {
    loadDetail()
  }, [sessionId])

  useEffect(() => {
    if (!sessionId) return
    loadStateMarket(seasonNumber)
  }, [sessionId, seasonNumber])

  const handleTrade = async (action) => {
    try {
      setBusy(true)
      setError('')
      const res = await api.trade({
        sessionId,
        seasonNumber,
        action,
        catType,
        catSex,
        counterpartyType: 'shop',
        counterpartyId: 1,
        qty: safeNum(qty, 1),
      })
      if (!res.ok) throw new Error(res.error || 'Trade failed')
      setState(res.state)
    } catch (err) {
      setError(err.message || 'Trade failed')
    } finally {
      setBusy(false)
    }
  }

  const handleCreditTake = async () => {
    try {
      setBusy(true)
      setError('')
      const res = await api.creditTake({
        sessionId,
        seasonNumber,
        creditType,
        amount: safeNum(creditAmount, 1),
      })
      if (!res.ok) throw new Error(res.error || 'Credit take failed')
      setState(res.state)
    } catch (err) {
      setError(err.message || 'Credit take failed')
    } finally {
      setBusy(false)
    }
  }

  const handleCreditRepay = async () => {
    try {
      setBusy(true)
      setError('')
      const res = await api.creditRepay({
        sessionId,
        seasonNumber,
        amount: safeNum(creditAmount, 1),
      })
      if (!res.ok) throw new Error(res.error || 'Credit repay failed')
      setState(res.state)
    } catch (err) {
      setError(err.message || 'Credit repay failed')
    } finally {
      setBusy(false)
    }
  }

  const finishSeason = async (finishEarly) => {
    try {
      setBusy(true)
      setError('')
      const res = await api.finishSeason(sessionId, seasonNumber, finishEarly)
      const nextSeason = res?.nextSeason?.number || seasonNumber
      await loadDetail(nextSeason)
      await loadStateMarket(nextSeason)
    } catch (err) {
      setError(err.message || 'Failed to finish season')
    } finally {
      setBusy(false)
    }
  }

  const finishSession = async () => {
    try {
      setBusy(true)
      setError('')
      await api.finishSession(sessionId)
      await loadDetail()
    } catch (err) {
      setError(err.message || 'Failed to finish session')
    } finally {
      setBusy(false)
    }
  }

  const stateMarket = market?.market || state?.market || {}
  const inventory = state?.inventory || {}
  const coinsNow = state?.coinsNowEstimate ?? 0
  const debtTotal = state?.debtTotal ?? 0
  const debtRate = state?.debtRate ?? 0

  return (
    <div className="page">
      <div className="page-header">
        <h1>Session</h1>
        <div className="actions">
          <button className="btn btn-secondary" onClick={() => navigate(`/analytics/${sessionId}`)}>
            Open results
          </button>
          <a
            className="btn btn-secondary"
            href={api.reportUrl(sessionId)}
            target="_blank"
            rel="noreferrer"
          >
            Download PDF
          </a>
          <button className="btn btn-secondary" onClick={() => navigate('/sessions')}>
            Back
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="muted">Loading session...</div>
      ) : (
        <>
          <div className="card">
            <div className="row">
              <span className="pill">{session?.status || 'unknown'}</span>
              <span className="pill">{session?.assignedRole || '—'}</span>
              <span className="pill">season {seasonNumber} / {Math.max(13, maxSeason)}</span>
            </div>
            <div className="muted" style={{ marginTop: 8 }}>
              Session ID: {sessionId}
            </div>
            <div className="row" style={{ marginTop: 8 }}>
              <div>Started: {fmt(session?.startedAt)}</div>
              <div>Finished: {fmt(session?.finishedAt)}</div>
            </div>
          <div className="row" style={{ marginTop: 8 }}>
            <div>Player: {session?.resultCoinsPlayer ?? '—'}</div>
            <div>Bot: {session?.resultCoinsBot ?? '—'}</div>
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            Current season: {currentSeason?.season_number ?? '—'} | coins: {currentSeason?.coins_end ?? '—'} | profit: {currentSeason?.profit ?? '—'}
          </div>
          <div className="actions" style={{ marginTop: 12 }}>
            <button
              className="btn btn-secondary"
              onClick={() => loadStateMarket(seasonNumber)}
            >
                Refresh state/market
              </button>
            </div>
          </div>

          <div className="grid-2">
            <div className="card">
              <div className="section-title">State</div>
              <div className="row">
                <span className="pill">coinsNow: {coinsNow}</span>
                <span className="pill">debt: {debtTotal}</span>
                <span className="pill">rate: {(debtRate * 100).toFixed(1)}%</span>
              </div>
              <div className="section-title" style={{ marginTop: 16 }}>
                Inventory
              </div>
              <div className="row">
                {CAT_TYPES.map((ct) => (
                  <span className="pill" key={ct}>
                    {ct}: {inventory[ct] ?? 0}
                  </span>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="section-title">Market</div>
              <table className="table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Buy</th>
                    <th>Sell</th>
                  </tr>
                </thead>
                <tbody>
                  {CAT_TYPES.map((ct) => (
                    <tr key={ct}>
                      <td>{ct}</td>
                      <td>{stateMarket?.[ct]?.buy ?? '—'}</td>
                      <td>{stateMarket?.[ct]?.sell ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid-2">
            <div className="card">
              <div className="section-title">Trade</div>
              <div className="row">
                <select
                  className="select"
                  value={catType}
                  onChange={(e) => setCatType(e.target.value)}
                >
                  {CAT_TYPES.map((ct) => (
                    <option value={ct} key={ct}>{ct}</option>
                  ))}
                </select>
                <input
                  className="input"
                  type="number"
                  value={qty}
                  onChange={(e) => setQty(e.target.value)}
                  min="1"
                />
                <button
                  className="btn"
                  onClick={() => handleTrade('buy')}
                  disabled={busy || isFinished}
                >
                  BUY
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleTrade('sell')}
                  disabled={busy || isFinished}
                >
                  SELL
                </button>
              </div>
              {isFinished && (
                <div className="muted" style={{ marginTop: 8 }}>
                  Session finished. Trading disabled.
                </div>
              )}
            </div>

            <div className="card">
              <div className="section-title">Credits</div>
              <div className="row">
                <input
                  className="input"
                  type="number"
                  value={creditAmount}
                  onChange={(e) => setCreditAmount(e.target.value)}
                  min="1"
                />
                <select
                  className="select"
                  value={creditType}
                  onChange={(e) => setCreditType(e.target.value)}
                >
                  <option value="consumer">consumer</option>
                  <option value="investment">investment</option>
                  <option value="special">special</option>
                </select>
                <button
                  className="btn"
                  onClick={handleCreditTake}
                  disabled={busy || isFinished}
                >
                  TAKE
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={handleCreditRepay}
                  disabled={busy || isFinished}
                >
                  REPAY
                </button>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="section-title">Finish</div>
            <div className="actions">
              <button
                className="btn"
                onClick={() => finishSeason(false)}
                disabled={busy || isFinished}
              >
                Finish season
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => finishSeason(true)}
                disabled={busy || isFinished}
              >
                Finish early
              </button>
              <button
                className="btn btn-secondary"
                onClick={finishSession}
                disabled={busy || isFinished}
              >
                Finish session
              </button>
            </div>
          </div>

          <div className="card">
            <div className="section-title">Seasons history</div>
            {seasons.length === 0 ? (
              <div className="muted">No seasons yet.</div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Season</th>
                    <th>Profit</th>
                    <th>Coins end</th>
                    <th>Meta</th>
                  </tr>
                </thead>
                <tbody>
                  {seasons.map((s) => (
                    <tr key={s.season_number}>
                      <td>{s.season_number}</td>
                      <td>{s.profit}</td>
                      <td>{s.coins_end}</td>
                      <td className="muted">{short(s.meta_json)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  )
}
