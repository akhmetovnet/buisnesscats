import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import './PlatformPages.css'

function formatDelta(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num) || Math.abs(num) < 0.001) return '0.00'
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}`
}

export default function CompetenciesPage() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)

  const formatDateTime = (value) => {
    if (!value) return '—'
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return '—'
    return d.toLocaleString()
  }

  useEffect(() => {
    let active = true
    const run = async () => {
      try {
        setLoading(true)
        setError('')
        const [summary, activeResponse] = await Promise.all([
          api.competenciesSummary(),
          api.activeSession(),
        ])
        if (active) {
          setData(summary)
          setActiveSession(activeResponse?.hasActive ? activeResponse.session : null)
        }
      } catch (err) {
        if (active) setError(err.message || 'Не удалось загрузить компетенции')
      } finally {
        if (active) setLoading(false)
      }
    }
    run()
    return () => {
      active = false
    }
  }, [])

  const handleStart = async () => {
    try {
      setStarting(true)
      setError('')
      const latestActive = activeSession?.id
        ? { hasActive: true, session: activeSession }
        : await api.activeSession()

      if (latestActive?.hasActive && latestActive?.session?.id) {
        const cont = await api.sessionsContinue(latestActive.session.id)
        navigate(`/play/${cont.sessionId}/${cont.seasonNumber}`)
        return
      }
      const created = await api.sessionsStart()
      setActiveSession({
        id: created.sessionId,
        status: created.status || 'ACTIVE',
        role: activeSession?.role || 'cattery',
        seasonNumber: Number(created.seasonNumber || 1),
        startedAt: new Date().toISOString(),
      })
      navigate(`/play/${created.sessionId}/${created.seasonNumber || 1}`)
    } catch (err) {
      setError(err.message || 'Не удалось начать игру')
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="platform-page">
      <section className="hero-card">
        <img className="hero-card__mascot" src="/assets/cats/dialoge-sleep-cat.png" alt="Business cat" />
        <div className="hero-card__content">
          <h1>Прокачай свой уровень в наших симуляциях</h1>
          <p>Проходи симуляции, улучшай результаты и развивай ключевые компетенции.</p>
        </div>
        <div className="hero-card__actions">
          <button className="platform-primary-btn" type="button" onClick={handleStart} disabled={starting}>
            {starting ? 'Запуск...' : activeSession?.id ? 'Продолжить' : 'Начать играть'}
          </button>
        </div>
      </section>

      {activeSession?.id ? (
        <section className="platform-card platform-card--active-session">
          <div className="platform-card__title">У вас есть активная сессия</div>
          <p className="platform-muted">
            Вы уже начали прохождение Business Cats. Продолжите текущую сессию, чтобы завершить все сезоны.
          </p>
          <div className="platform-form-grid platform-form-grid--session">
            <div><b>Симуляция:</b> Business Cats</div>
            <div><b>Статус:</b> Активна</div>
            <div><b>Роль:</b> {activeSession.role === 'petshop' ? 'Магазин' : 'Питомник'}</div>
            <div><b>Начата:</b> {formatDateTime(activeSession.startedAt)}</div>
            <div><b>Прогресс:</b> Сезон {Number(activeSession.seasonNumber || 1)} из 13</div>
          </div>
          <div className="platform-actions-row">
            <button
              type="button"
              className="platform-primary-btn"
              onClick={handleStart}
              disabled={starting}
            >
              {starting ? 'Переход...' : 'Продолжить игру'}
            </button>
          </div>
        </section>
      ) : null}

      <section className="platform-card">
        <div className="platform-card__title">Основные компетенции</div>
        {error ? <div className="platform-error">{error}</div> : null}
        {loading ? (
          <div className="platform-muted">Загрузка компетенций...</div>
        ) : (
          <div className="competencies-grid">
            {(data?.items || []).map((item) => (
              <article className="competency-card" key={item.code}>
                <div className="competency-card__head">
                  <span className="competency-card__dot" style={{ backgroundColor: item.color }}>
                    {item.title.slice(0, 1)}
                  </span>
                  <h3>{item.title}</h3>
                </div>
                <div className="competency-card__meta">
                  <span className="competency-card__value">{Number(item.level).toFixed(2)}</span>
                  <span className={`competency-card__delta ${Number(item.delta) >= 0 ? 'is-positive' : 'is-negative'}`}>
                    {formatDelta(item.delta)}
                  </span>
                </div>
                <div className="competency-card__subtitle">Ваш уровень</div>
                <div className="competency-progress">
                  <div className="competency-progress__track" />
                  <div
                    className="competency-progress__fill"
                    style={{ width: `${Math.max(0, Math.min(100, Number(item.progress) * 100))}%`, backgroundColor: item.color }}
                  />
                </div>
              </article>
            ))}
          </div>
        )}
        {!loading && data?.empty ? (
          <div className="platform-muted" style={{ marginTop: 14 }}>
            Завершите первую симуляцию, чтобы получить прогресс.
            <div className="platform-actions-row">
              <button className="platform-secondary-btn" type="button" onClick={handleStart} disabled={starting}>
                Начните первую симуляцию
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  )
}
