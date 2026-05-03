// Priority badge — shows P0/P1/P2 with color
export function PriorityBadge({ priority }) {
  const styles = {
    P0: 'bg-red-600 text-white',
    P1: 'bg-yellow-500 text-black',
    P2: 'bg-blue-500 text-white',
  }
  return (
    <span className={`px-2 py-1 rounded text-xs font-bold ${styles[priority] || 'bg-gray-600'}`}>
      {priority}
    </span>
  )
}

// Status badge — shows OPEN/INVESTIGATING/RESOLVED/CLOSED
export function StatusBadge({ status }) {
  const styles = {
    OPEN: 'bg-red-900 text-red-300 border border-red-700',
    INVESTIGATING: 'bg-yellow-900 text-yellow-300 border border-yellow-700',
    RESOLVED: 'bg-blue-900 text-blue-300 border border-blue-700',
    CLOSED: 'bg-green-900 text-green-300 border border-green-700',
  }
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || 'bg-gray-700 text-gray-300'}`}>
      {status}
    </span>
  )
}

// Component type badge
export function ComponentBadge({ type }) {
  const colors = {
    RDBMS: 'bg-purple-800 text-purple-200',
    NOSQL: 'bg-indigo-800 text-indigo-200',
    CACHE: 'bg-cyan-800 text-cyan-200',
    API: 'bg-teal-800 text-teal-200',
    QUEUE: 'bg-orange-800 text-orange-200',
    MCP_HOST: 'bg-pink-800 text-pink-200',
  }
  return (
    <span className={`px-2 py-1 rounded text-xs ${colors[type] || 'bg-gray-700 text-gray-300'}`}>
      {type}
    </span>
  )
}
