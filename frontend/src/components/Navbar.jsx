import { Link, useLocation } from 'react-router-dom'

export function Navbar({ wsConnected }) {
  const location = useLocation()

  return (
    <nav className="bg-gray-900 border-b border-gray-700 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3">
          <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">⚡</span>
          </div>
          <div>
            <div className="text-white font-bold text-lg leading-none">IMS</div>
            <div className="text-gray-400 text-xs">Incident Management System</div>
          </div>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-6">
          <Link
            to="/"
            className={`text-sm font-medium transition-colors ${
              location.pathname === '/' ? 'text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Dashboard
          </Link>
          <Link
            to="/simulate"
            className={`text-sm font-medium transition-colors ${
              location.pathname === '/simulate' ? 'text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Simulate
          </Link>
        </div>

        {/* WS connection status */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-xs text-gray-400">
            {wsConnected ? 'Live' : 'Connecting...'}
          </span>
        </div>
      </div>
    </nav>
  )
}
