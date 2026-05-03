import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getIncidents } from '../api'
import { PriorityBadge, StatusBadge, ComponentBadge } from '../components/Badges'
import { formatDistanceToNow } from 'date-fns'

const STATUS_FILTERS = ['ALL', 'OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED']

export function Dashboard({ wsMessage }) {
  const [incidents, setIncidents] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')
  const [lastRefresh, setLastRefresh] = useState(null)
  const navigate = useNavigate()

  const fetchIncidents = useCallback(async () => {
    try {
      const res = await getIncidents(filter === 'ALL' ? null : filter)
      setIncidents(res.data.items)
      setTotal(res.data.total)
      setLastRefresh(new Date())
    } catch (err) {
      console.error('Failed to fetch incidents', err)
    } finally {
      setLoading(false)
    }
  }, [filter])

  // Initial load + auto-refresh every 5 seconds
  useEffect(() => {
    fetchIncidents()
    const interval = setInterval(fetchIncidents, 5000)
    return () => clearInterval(interval)
  }, [fetchIncidents])

  // Refresh when WebSocket sends an update
  useEffect(() => {
    if (wsMessage?.type === 'incident_update') {
      fetchIncidents()
    }
  }, [wsMessage])

  const stats = {
    P0: incidents.filter(i => i.priority === 'P0' && i.status !== 'CLOSED').length,
    P1: incidents.filter(i => i.priority === 'P1' && i.status !== 'CLOSED').length,
    P2: incidents.filter(i => i.priority === 'P2' && i.status !== 'CLOSED').length,
    open: incidents.filter(i => i.status === 'OPEN').length,
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Incident Feed</h1>
          <p className="text-gray-400 text-sm mt-1">
            {lastRefresh
              ? `Last updated ${formatDistanceToNow(lastRefresh, { addSuffix: true })}`
              : 'Loading...'}
          </p>
        </div>
        <button
          onClick={fetchIncidents}
          className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="P0 Critical" value={stats.P0} color="red" />
        <StatCard label="P1 High" value={stats.P1} color="yellow" />
        <StatCard label="P2 Medium" value={stats.P2} color="blue" />
        <StatCard label="Open Total" value={stats.open} color="gray" />
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-6">
        {STATUS_FILTERS.map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-4 py-1.5 rounded-full text-xs font-medium transition-colors ${
              filter === s
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white border border-gray-700'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Incidents table */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">Loading incidents...</div>
      ) : incidents.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-4xl mb-3">✓</div>
          <div>No incidents found. System is healthy!</div>
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map(incident => (
            <div
              key={incident.id}
              onClick={() => navigate(`/incidents/${incident.id}`)}
              className="bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-gray-500 rounded-xl px-5 py-4 cursor-pointer transition-all"
            >
              <div className="flex items-center justify-between">
                {/* Left: priority + title */}
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <PriorityBadge priority={incident.priority} />
                  <div className="min-w-0">
                    <div className="text-white font-medium truncate">{incident.title}</div>
                    <div className="text-gray-400 text-xs mt-0.5">
                      {incident.component_id} · {incident.signal_count} signals ·{' '}
                      {formatDistanceToNow(new Date(incident.start_time), { addSuffix: true })}
                    </div>
                  </div>
                </div>

                {/* Right: badges */}
                <div className="flex items-center gap-2 ml-4 shrink-0">
                  <ComponentBadge type={incident.component_type} />
                  <StatusBadge status={incident.status} />
                  {incident.mttr_minutes && (
                    <span className="text-xs text-green-400">
                      MTTR: {incident.mttr_minutes}m
                    </span>
                  )}
                  <span className="text-gray-500 text-sm">→</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500 text-right">
        Showing {incidents.length} of {total} incidents
      </div>
    </div>
  )
}

function StatCard({ label, value, color }) {
  const colors = {
    red: 'border-red-800 bg-red-900/20 text-red-400',
    yellow: 'border-yellow-800 bg-yellow-900/20 text-yellow-400',
    blue: 'border-blue-800 bg-blue-900/20 text-blue-400',
    gray: 'border-gray-700 bg-gray-800 text-gray-300',
  }
  return (
    <div className={`border rounded-xl p-4 ${colors[color]}`}>
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-xs mt-1 opacity-80">{label}</div>
    </div>
  )
}
