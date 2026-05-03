import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getIncident, getIncidentSignals, updateIncidentStatus } from '../api'
import { PriorityBadge, StatusBadge, ComponentBadge } from '../components/Badges'
import { RCAForm } from '../components/RCAForm'
import { formatDistanceToNow, format } from 'date-fns'

const STATUS_FLOW = ['OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED']

const NEXT_STATUS = {
  OPEN: 'INVESTIGATING',
  INVESTIGATING: 'RESOLVED',
  RESOLVED: 'CLOSED',
  CLOSED: null,
}

const NEXT_LABEL = {
  OPEN: '▶ Start Investigating',
  INVESTIGATING: '✓ Mark Resolved',
  RESOLVED: '🔒 Close Incident',
  CLOSED: null,
}

export function IncidentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [incident, setIncident] = useState(null)
  const [signals, setSignals] = useState([])
  const [loading, setLoading] = useState(true)
  const [transitioning, setTransitioning] = useState(false)
  const [error, setError] = useState(null)
  const [showRCA, setShowRCA] = useState(false)

  const fetchData = async () => {
    try {
      const [incRes, sigRes] = await Promise.all([
        getIncident(id),
        getIncidentSignals(id),
      ])
      setIncident(incRes.data)
      setSignals(sigRes.data.signals)
    } catch (err) {
      setError('Failed to load incident')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [id])

  const handleTransition = async () => {
    const next = NEXT_STATUS[incident.status]
    if (!next) return

    // If closing and no RCA, show RCA form
    if (next === 'CLOSED' && !incident.rca) {
      setShowRCA(true)
      return
    }

    setTransitioning(true)
    setError(null)
    try {
      await updateIncidentStatus(id, next)
      await fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update status')
    } finally {
      setTransitioning(false)
    }
  }

  if (loading) return <div className="text-center py-16 text-gray-400">Loading...</div>
  if (!incident) return <div className="text-center py-16 text-red-400">Incident not found</div>

  const nextStatus = NEXT_STATUS[incident.status]
  const currentStep = STATUS_FLOW.indexOf(incident.status)

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Back button */}
      <button
        onClick={() => navigate('/')}
        className="text-gray-400 hover:text-white text-sm mb-6 flex items-center gap-2 transition-colors"
      >
        ← Back to Dashboard
      </button>

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-300 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      {/* Header card */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <PriorityBadge priority={incident.priority} />
              <ComponentBadge type={incident.component_type} />
              <StatusBadge status={incident.status} />
            </div>
            <h1 className="text-xl font-bold text-white mb-1">{incident.title}</h1>
            <p className="text-gray-400 text-sm">{incident.description}</p>
          </div>

          {/* Advance status button */}
          {nextStatus && (
            <button
              onClick={handleTransition}
              disabled={transitioning}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shrink-0"
            >
              {transitioning ? 'Updating...' : NEXT_LABEL[incident.status]}
            </button>
          )}
        </div>

        {/* Status progress bar */}
        <div className="mt-6">
          <div className="flex items-center gap-0">
            {STATUS_FLOW.map((s, i) => (
              <div key={s} className="flex items-center flex-1">
                <div className="flex flex-col items-center">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    i <= currentStep ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-500'
                  }`}>
                    {i < currentStep ? '✓' : i + 1}
                  </div>
                  <span className="text-xs text-gray-400 mt-1">{s}</span>
                </div>
                {i < STATUS_FLOW.length - 1 && (
                  <div className={`h-0.5 flex-1 mx-1 ${i < currentStep ? 'bg-blue-600' : 'bg-gray-700'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Meta info */}
        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-gray-700">
          <div>
            <div className="text-xs text-gray-500 mb-1">Component</div>
            <div className="text-sm text-white font-mono">{incident.component_id}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">Started</div>
            <div className="text-sm text-white">
              {formatDistanceToNow(new Date(incident.start_time), { addSuffix: true })}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">Signals</div>
            <div className="text-sm text-white">{incident.signal_count} error signals</div>
          </div>
          {incident.mttr_minutes && (
            <div>
              <div className="text-xs text-gray-500 mb-1">MTTR</div>
              <div className="text-sm text-green-400 font-bold">{incident.mttr_minutes} minutes</div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Raw signals from MongoDB */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h2 className="text-lg font-bold text-white mb-4">
            Raw Signals ({signals.length})
          </h2>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {signals.length === 0 ? (
              <div className="text-gray-500 text-sm">No signals yet</div>
            ) : (
              signals.map((sig, i) => (
                <div key={i} className="bg-gray-900 rounded-lg p-3 text-xs font-mono">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-red-400 font-bold">{sig.error_code}</span>
                    <span className="text-gray-500">
                      {sig.latency_ms ? `${sig.latency_ms}ms` : ''}
                    </span>
                  </div>
                  <div className="text-gray-300 truncate">{sig.message}</div>
                  <div className="text-gray-600 mt-1">
                    {sig.timestamp ? format(new Date(sig.timestamp), 'HH:mm:ss') : ''}
                    {sig.debounced && <span className="ml-2 text-yellow-600">[debounced]</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* RCA section */}
        <div>
          {incident.rca ? (
            <div className="bg-gray-800 rounded-xl p-5 border border-green-800">
              <h2 className="text-lg font-bold text-white mb-4">✓ RCA Submitted</h2>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-gray-400">Category: </span>
                  <span className="text-white">{incident.rca.root_cause_category}</span>
                </div>
                <div>
                  <span className="text-gray-400">Fix: </span>
                  <span className="text-gray-300">{incident.rca.fix_applied}</span>
                </div>
                <div>
                  <span className="text-gray-400">Prevention: </span>
                  <span className="text-gray-300">{incident.rca.prevention_steps}</span>
                </div>
                <div>
                  <span className="text-gray-400">By: </span>
                  <span className="text-gray-300">{incident.rca.submitted_by}</span>
                </div>
              </div>

              {incident.status === 'RESOLVED' && (
                <button
                  onClick={handleTransition}
                  disabled={transitioning}
                  className="mt-4 w-full bg-green-700 hover:bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  🔒 Close Incident
                </button>
              )}
            </div>
          ) : showRCA || incident.status === 'RESOLVED' ? (
            <RCAForm
              incidentId={id}
              onSuccess={() => {
                setShowRCA(false)
                fetchData()
              }}
            />
          ) : (
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 text-center">
              <div className="text-4xl mb-3">📋</div>
              <div className="text-gray-400 text-sm">
                RCA form will appear when incident is RESOLVED
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
