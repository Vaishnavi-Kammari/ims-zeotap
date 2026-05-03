import { useState } from 'react'
import { submitRCA } from '../api'

const ROOT_CAUSE_OPTIONS = [
  'INFRASTRUCTURE',
  'APPLICATION',
  'NETWORK',
  'DATABASE',
  'HUMAN_ERROR',
  'THIRD_PARTY',
  'UNKNOWN',
]

export function RCAForm({ incidentId, onSuccess }) {
  const [form, setForm] = useState({
    incident_start: '',
    incident_end: '',
    root_cause_category: 'INFRASTRUCTURE',
    fix_applied: '',
    prevention_steps: '',
    submitted_by: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await submitRCA(incidentId, form)
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit RCA')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-bold text-white mb-1">Root Cause Analysis</h2>
      <p className="text-gray-400 text-sm mb-6">
        Fill this form completely before closing the incident.
      </p>

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-300 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Date/time pickers */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Incident Start *</label>
            <input
              type="datetime-local"
              name="incident_start"
              value={form.incident_start}
              onChange={handleChange}
              required
              className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Incident End *</label>
            <input
              type="datetime-local"
              name="incident_end"
              value={form.incident_end}
              onChange={handleChange}
              required
              className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Root cause category dropdown */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Root Cause Category *</label>
          <select
            name="root_cause_category"
            value={form.root_cause_category}
            onChange={handleChange}
            required
            className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          >
            {ROOT_CAUSE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt.replace('_', ' ')}</option>
            ))}
          </select>
        </div>

        {/* Fix applied */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Fix Applied *</label>
          <textarea
            name="fix_applied"
            value={form.fix_applied}
            onChange={handleChange}
            required
            rows={3}
            placeholder="Describe exactly what was done to fix the issue..."
            className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>

        {/* Prevention steps */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Prevention Steps *</label>
          <textarea
            name="prevention_steps"
            value={form.prevention_steps}
            onChange={handleChange}
            required
            rows={3}
            placeholder="How will you prevent this from happening again?..."
            className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>

        {/* Submitted by */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Submitted By</label>
          <input
            type="text"
            name="submitted_by"
            value={form.submitted_by}
            onChange={handleChange}
            placeholder="Your name (optional)"
            className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm"
        >
          {loading ? 'Submitting...' : 'Submit RCA'}
        </button>
      </form>
    </div>
  )
}
