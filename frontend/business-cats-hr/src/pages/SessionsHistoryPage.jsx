import { useEffect, useState } from 'react'
import { api } from '../api.js'
import './PlatformPages.css'

const fmt = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString()
}

function deltaClass(value) {
  return Number(value || 0) >= 0 ? 'is-positive' : 'is-negative'
}

function deltaText(value) {
  const num = Number(value || 0)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}`
}

function reasonLabel(value) {
  if (value === 'BANKRUPT_INACTIVITY') return 'Банкротство: бездействие'
  if (value === 'BANKRUPT_MONEY') return 'Банкротство: деньги'
  if (value === 'NORMAL_COMPLETION') return 'Завершена нормально'
  return '—'
}

export default function SessionsHistoryPage() {
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState(null)
  const [details, setDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const run = async () => {
      try {
        setLoading(true)
        setError('')
        const response = await api.sessionsHistory()
        if (active) setItems(response?.items || [])
      } catch (err) {
        if (active) setError(err.message || 'Не удалось загрузить историю')
      } finally {
        if (active) setLoading(false)
      }
    }
    run()
    return () => {
      active = false
    }
  }, [])

  const openDetails = async (id) => {
    try {
      setSelected(id)
      setError('')
      const response = await api.sessionsDetails(id)
      setDetails(response)
    } catch (err) {
      setError(err.message || 'Не удалось загрузить детали сессии')
    }
  }

  return (
    <div className="platform-page">
      <section className="platform-card">
        <div className="platform-card__title">История сессий</div>
        {error ? <div className="platform-error">{error}</div> : null}
        {loading ? (
          <div className="platform-muted">Загрузка...</div>
        ) : items.length === 0 ? (
          <div className="platform-muted">Сессий пока нет.</div>
        ) : (
          <div className="history-table-wrap">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Симуляция</th>
                  <th>Роль</th>
                  <th>Статус</th>
                  <th>Активна сейчас</th>
                  <th>Причина завершения</th>
                  <th>Место</th>
                  <th>Баланс</th>
                  <th>Дата старта</th>
                  <th>Дата финиша</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((session) => (
                  <tr key={session.id}>
                    <td>{session.simulation}</td>
                    <td>{session.role}</td>
                    <td>{session.status}</td>
                    <td>{session.wasActiveAtView ? 'Да' : 'Нет'}</td>
                    <td>{reasonLabel(session.reasonCompleted)}</td>
                    <td>{session.finalPlace || '—'}</td>
                    <td>{session.finalBalance}</td>
                    <td>{fmt(session.startedAt)}</td>
                    <td>{fmt(session.finishedAt)}</td>
                    <td>
                      <button className="platform-link-btn" type="button" onClick={() => openDetails(session.id)}>
                        Детали
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && details ? (
        <section className="platform-card">
          <div className="platform-card__title">Детали сессии {selected.slice(0, 8)}</div>
          <div className="platform-form-grid">
            <div><b>Статус:</b> {details.status}</div>
            <div><b>Активна на момент просмотра:</b> {details.wasActiveAtView ? 'Да' : 'Нет'}</div>
            <div><b>Место:</b> {details.finalPlace || '—'}</div>
            <div><b>Итоговый баланс:</b> {details.finalBalance}</div>
            <div><b>Причина завершения:</b> {details.reason || '—'}</div>
            <div><b>Код причины:</b> {reasonLabel(details.reasonCompleted)}</div>
            <div><b>Пройдено сезонов:</b> {details.seasonCountCompleted}</div>
          </div>

          <div className="history-delta-row">
            <span>Аналитика: <b className={deltaClass(details.competencyDelta.analytics)}>{deltaText(details.competencyDelta.analytics)}</b></span>
            <span>Переговоры: <b className={deltaClass(details.competencyDelta.negotiation)}>{deltaText(details.competencyDelta.negotiation)}</b></span>
            <span>Стратегическое управление: <b className={deltaClass(details.competencyDelta.strategy)}>{deltaText(details.competencyDelta.strategy)}</b></span>
          </div>
        </section>
      ) : null}
    </div>
  )
}
