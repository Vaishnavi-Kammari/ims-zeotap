import { useState, useCallback } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Navbar } from './components/Navbar'
import { Dashboard } from './pages/Dashboard'
import { IncidentDetail } from './pages/IncidentDetail'
import { Simulate } from './pages/Simulate'
import { useWebSocket } from './hooks/useWebSocket'

export default function App() {
  const [lastWsMessage, setLastWsMessage] = useState(null)

  const handleWsMessage = useCallback((msg) => {
    setLastWsMessage(msg)
  }, [])

  const { connected } = useWebSocket(handleWsMessage)

  return (
    <div className="min-h-screen bg-gray-950">
      <Navbar wsConnected={connected} />
      <Routes>
        <Route path="/" element={<Dashboard wsMessage={lastWsMessage} />} />
        <Route path="/incidents/:id" element={<IncidentDetail />} />
        <Route path="/simulate" element={<Simulate />} />
      </Routes>
    </div>
  )
}
