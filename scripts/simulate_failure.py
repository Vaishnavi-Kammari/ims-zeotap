import { useState } from 'react'
import { sendBatchSignals } from '../api'

const SCENARIOS = [
  {
    name: '🔴 RDBMS Outage (P0)',
    description: 'Simulates a PostgreSQL primary database failure. Sends 150 signals — only 1 work item created (debounce demo)',
    count: 150,
    signal: {
      component_id: 'POSTGRES_MAIN_01',
      component_type: 'RDBMS',
      error_code: 'CONNECTION_TIMEOUT',
      message: 'Primary database connection pool exhausted. All queries failing.',
      latency_ms: 5000,
    },
  },
  {
    name: '🟡 API Gateway Slowdown (P1)',
    description: 'Simulates an API gateway experiencing high latency and 5xx errors',
    count: 50,
    signal: {
      component_id: 'API_GATEWAY_01',
      component_type: 'API',
      error_code: 'HTTP_503',
      message: 'Service unavailable. Upstream timeout after 30s.',
      latency_ms: 30000,
    },
  },
  {
    name: '🔵 Cache Miss Spike (P2)',
    description: 'Simulates a Redis cache cluster with high miss rate',
    count: 30,
    signal: {
      component_id: 'CACHE_CLUSTER_01',
      component_type: 'CACHE',
      error_code: 'CACHE_MISS',
      message: 'Cache miss rate exceeded 80%. Falling back to database.',
      latency_ms: 800,
    },
  },
  {
    name: '🔴 MCP Host Failure (P0)',
    description: 'Simulates a critical MCP host going down',
    count: 80,
    signal: {
      component_id: 'MCP_HOST_PROD_01',
      component_type: 'MCP_HOST',
      error_code: 'HOST_UNREACHABLE',
      message: 'MCP host not responding. Health check failed 3 consecutive times.',
      latency_ms: null,
    },
  },
  {
    name: '🟡 Message Queue Backlog (P1)',
    description: 'Simulates async queue backing up with unprocessed messages',
    count: 40,
    signal: {
      component_id: 'KAFKA_CLUSTER_01',
      component_type: 'QUEUE',
      error_code: 'CONSUMER_LAG',
      message: 'Consumer group lag exceeded 100k messages. Processing delayed.',
      latency_ms: null,
    },
  },
]

export function Simulate() {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(null)

  const runScenario = async (scenario) => {
    setLoading(scenario.name)
    try {
      // Send signals in batches of 100
      const batches = []
      let remaining = scenario.count
      while (remaining > 0) {
        const batchSize = Math.min(remaining, 100)
        batches.push(Array(batchSize).fill(scenario.signal))
        remaining -= batchSize
      }

      let totalAccepted = 0
      for (const batch of batches) {
        const res = await sendBatchSignals(batch)
        totalAccepted += res.data.accepted
        await new Promise(r => setTimeout(r, 100)) // small delay between batches
      }

      setResults(prev => [{
        scenario: scenario.name,
        sent: scenario.count,
        accepted: totalAccepted,
        time: new Date().toLocaleTimeString(),
        success: true,
      }, ...prev.slice(0, 9)])
    } catch (err) {
      setResults(prev => [{
        scenario: scenario.name,
        error: err.message,
        time: new Date().toLocaleTimeString(),
        success: false,
      }, ...prev.slice(0, 9)])
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Simulate Failures</h1>
        <p className="text-gray-400 text-sm mt-1">
          Click a scenario to send signals to the IMS. Watch the dashboard update in real time.
        </p>
      </div>

      {/* Scenarios */}
      <div className="grid grid-cols-1 gap-4 mb-8">
        {SCENARIOS.map((scenario) => (
          <div
            key={scenario.name}
            className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex items-center justify-between"
          >
            <div className="flex-1">
              <div className="font-semibold text-white mb-1">{scenario.name}</div>
              <div className="text-gray-400 text-sm mb-2">{scenario.description}</div>
              <div className="flex gap-4 text-xs text-gray-500">
                <span>Component: <code className="text-gray-300">{scenario.signal.component_id}</code></span>
                <span>Signals: <span className="text-gray-300">{scenario.count}</span></span>
                <span>Error: <code className="text-red-400">{scenario.signal.error_code}</code></span>
              </div>
            </div>
            <button
              onClick={() => runScenario(scenario)}
              disabled={loading !== null}
              className="ml-6 bg-red-700 hover:bg-red-600 disabled:bg-gray-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors shrink-0"
            >
              {loading === scenario.name ? 'Sending...' : '▶ Run'}
            </button>
          </div>
        ))}
      </div>

      {/* Results log */}
      {results.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h2 className="text-lg font-bold text-white mb-4">Simulation Log</h2>
          <div className="space-y-2">
            {results.map((r, i) => (
              <div
                key={i}
                className={`flex items-center justify-between px-4 py-2 rounded-lg text-sm ${
                  r.success ? 'bg-green-900/30 border border-green-800' : 'bg-red-900/30 border border-red-800'
                }`}
              >
                <span className="text-white">{r.scenario}</span>
                {r.success ? (
                  <span className="text-green-400">
                    ✓ {r.accepted}/{r.sent} signals accepted · {r.time}
                  </span>
                ) : (
                  <span className="text-red-400">✗ {r.error} · {r.time}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
