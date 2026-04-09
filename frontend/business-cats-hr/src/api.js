async function parseResponse(response) {
  const text = await response.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  return data
}

function unavailableError(message) {
  const error = new Error(message || 'API server is unavailable. Start backend on http://127.0.0.1:8000')
  error.status = 0
  error.code = 'API_UNAVAILABLE'
  error.retryAfterSeconds = null
  return error
}

function toApiError(response, data) {
  if (response.status >= 500 && !data) {
    return unavailableError()
  }

  const detail = data?.detail
  const message =
    detail?.message ||
    (typeof detail === 'string' ? detail : null) ||
    data?.message ||
    data?.error ||
    response.statusText ||
    'Request failed'

  const error = new Error(message)
  error.status = response.status
  error.code = detail?.error || data?.error || null
  error.retryAfterSeconds = detail?.retryAfterSeconds || data?.retryAfterSeconds || null
  return error
}

export async function apiGet(path) {
  let response
  try {
    response = await fetch(path, {
      method: 'GET',
      credentials: 'include',
    })
  } catch {
    throw unavailableError()
  }
  const data = await parseResponse(response)
  if (!response.ok) {
    throw toApiError(response, data)
  }
  return data
}

export async function apiPost(path, body) {
  let response
  try {
    response = await fetch(path, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    })
  } catch {
    throw unavailableError()
  }
  const data = await parseResponse(response)
  if (!response.ok) {
    throw toApiError(response, data)
  }
  return data
}

export async function apiPatch(path, body) {
  let response
  try {
    response = await fetch(path, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    })
  } catch {
    throw unavailableError()
  }
  const data = await parseResponse(response)
  if (!response.ok) {
    throw toApiError(response, data)
  }
  return data
}

export async function apiDelete(path) {
  let response
  try {
    response = await fetch(path, {
      method: 'DELETE',
      credentials: 'include',
    })
  } catch {
    throw unavailableError()
  }
  const data = await parseResponse(response)
  if (!response.ok) {
    throw toApiError(response, data)
  }
  return data
}

export async function apiUpload(path, formData) {
  let response
  try {
    response = await fetch(path, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    })
  } catch {
    throw unavailableError()
  }
  const data = await parseResponse(response)
  if (!response.ok) {
    throw toApiError(response, data)
  }
  return data
}

export const api = {
  authRegister: (payload) => apiPost('/api/auth/register', payload),
  authLogin: (payload) => apiPost('/api/auth/login', payload),
  authRefresh: () => apiPost('/api/auth/refresh', {}),
  authLogout: () => apiPost('/api/auth/logout', {}),
  authLogoutAll: () => apiPost('/api/auth/logout-all', {}),
  authResendEmail: (payload) => apiPost('/api/auth/email/resend', payload),
  authResetRequest: (payload) => apiPost('/api/auth/password/reset/request', payload),
  authResetConfirm: (payload) => apiPost('/api/auth/password/reset/confirm', payload),
  me: () => apiGet('/api/me'),
  meProfile: () => apiGet('/api/me/profile'),
  meProfileUpdate: (payload) => apiPatch('/api/me/profile', payload),
  meAvatarUpload: (file) => {
    const data = new FormData()
    data.append('file', file)
    return apiUpload('/api/me/avatar', data)
  },
  meAvatarDelete: () => apiDelete('/api/me/avatar'),
  meChangePassword: (payload) => apiPost('/api/me/change-password', payload),

  competenciesSummary: () => apiGet('/api/competencies/summary'),

  activeSession: () => apiGet('/api/sessions/active'),
  sessionsStart: () => apiPost('/api/sessions/start', {}),
  sessionsContinue: (sessionId) => apiPost(`/api/sessions/${sessionId}/continue`, {}),
  sessionsHistory: () => apiGet('/api/sessions/history'),
  sessionsDetails: (sessionId) => apiGet(`/api/sessions/${sessionId}/details`),

  startSession: () => apiPost('/api/game/session/start'),
  finishSeason: (
    sessionId,
    seasonNumber,
    finishEarly = false,
    nursery = null,
    nurseryCoinsDelta = 0
  ) =>
    apiPost('/api/game/season/finish', {
      sessionId,
      seasonNumber,
      finishEarly,
      nursery,
      nurseryCoinsDelta,
    }),
  finishSession: (sessionId) => apiPost('/api/game/session/finish', { sessionId }),
  getProgress: (sessionId, seasonNumber) => apiGet(`/api/game/progress/${sessionId}/${seasonNumber}`),
  saveProgress: (payload) => apiPost('/api/game/progress/save', payload),

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
  tradeRequests: (sessionId, seasonNumber) => apiGet(`/api/game/trade-requests/${sessionId}/${seasonNumber}`),
  tradeRequestSend: (payload) => apiPost('/api/game/trade-requests/send', payload),
  tradeRequestAction: (requestId, payload) =>
    apiPost(`/api/game/trade-requests/${requestId}/action`, payload),
  catteryPublic: (sessionId, seasonNumber, catteryId) =>
    apiGet(`/api/game/cattery-public/${sessionId}/${seasonNumber}/${catteryId}`),
  tradeRequestsWsUrl: (sessionId) => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    return `${protocol}://${host}/api/game/trade-requests/ws/${sessionId}`
  },
  creditTake: (payload) => apiPost('/api/game/credit/take', payload),
  creditRepay: (payload) => apiPost('/api/game/credit/repay', payload),

  analytics: (sessionId) => apiPost(`/api/analytics/compute/${sessionId}`),
  reportUrl: (sessionId) => `/api/analytics/report/${sessionId}`,
}
