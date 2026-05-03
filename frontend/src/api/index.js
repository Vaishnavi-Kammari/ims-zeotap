import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// ── Incidents ────────────────────────────────────────────────────────────────

export const getIncidents = (status = null) => {
  const params = status ? { status } : {}
  return api.get('/incidents', { params })
}

export const getIncident = (id) => api.get(`/incidents/${id}`)

export const updateIncidentStatus = (id, status) =>
  api.patch(`/incidents/${id}/status`, { status })

export const getIncidentSignals = (id) => api.get(`/incidents/${id}/signals`)

// ── RCA ──────────────────────────────────────────────────────────────────────

export const submitRCA = (incidentId, data) =>
  api.post(`/incidents/${incidentId}/rca`, data)

// ── Signals ──────────────────────────────────────────────────────────────────

export const sendSignal = (data) => api.post('/signals', data)

export const sendBatchSignals = (data) => api.post('/signals/batch', data)

// ── Health ───────────────────────────────────────────────────────────────────

export const getHealth = () => api.get('/health')
