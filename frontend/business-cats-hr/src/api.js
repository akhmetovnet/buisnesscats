function demoHeaders() {
  const id = localStorage.getItem('demoUserId')
  return id ? { 'X-Demo-UserId': id } : {}
}

export async function apiGet(path) {
  const r = await fetch(path, { headers: { ...demoHeaders() } })
  const text = await r.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!r.ok) throw new Error(data?.detail || data?.error || r.statusText)
  return data
}

export async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...demoHeaders() },
    body: JSON.stringify(body ?? {}),
  })
  const text = await r.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!r.ok) throw new Error(data?.detail || data?.error || r.statusText)
  return data
}

export const api = {
  startSession: () => apiPost('/api/game/session/start'),
  finishSeason: (sessionId, seasonNumber, finishEarly = false) =>
    apiPost('/api/game/season/finish', { sessionId, seasonNumber, finishEarly }),
  finishSession: (sessionId) => apiPost('/api/game/session/finish', { sessionId }),

  sessions: () => apiGet('/api/game/sessions'),
  sessionDetail: (id) => apiGet(`/api/game/session/${id}`),

  state: (sessionId, seasonNumber, counterpartyType = null, counterpartyId = null) => {
    const params = new URLSearchParams()
    if (counterpartyType) params.set('counterpartyType', counterpartyType)
    if (Number.isFinite(Number(counterpartyId))) params.set('counterpartyId', String(counterpartyId))
    const query = params.toString()
    return apiGet(`/api/game/state/${sessionId}/${seasonNumber}${query ? `?${query}` : ''}`)
  },
  market: (sessionId, seasonNumber, counterpartyType = null, counterpartyId = null) => {
    const params = new URLSearchParams()
    if (counterpartyType) params.set('counterpartyType', counterpartyType)
    if (Number.isFinite(Number(counterpartyId))) params.set('counterpartyId', String(counterpartyId))
    const query = params.toString()
    return apiGet(`/api/game/market/${sessionId}/${seasonNumber}${query ? `?${query}` : ''}`)
  },
  getGameState: (sessionId, seasonNumber, counterpartyType = null, counterpartyId = null) =>
    api.state(sessionId, seasonNumber, counterpartyType, counterpartyId),
  getMarket: (sessionId, seasonNumber, counterpartyType = null, counterpartyId = null) =>
    api.market(sessionId, seasonNumber, counterpartyType, counterpartyId),

  trade: (payload) => apiPost('/api/game/trade', payload),
  creditTake: (payload) => apiPost('/api/game/credit/take', payload),
  creditRepay: (payload) => apiPost('/api/game/credit/repay', payload),

  analytics: (sessionId) => apiPost(`/api/analytics/compute/${sessionId}`),
  reportUrl: (sessionId) => `/api/analytics/report/${sessionId}`,
}
