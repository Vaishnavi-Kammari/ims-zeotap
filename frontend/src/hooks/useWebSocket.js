import { useEffect, useRef, useState, useCallback } from 'react'

export function useWebSocket(onMessage) {
  const ws = useRef(null)
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/ws/incidents`

    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      setConnected(true)
      console.log('WebSocket connected')
    }

    ws.current.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type !== 'keepalive' && msg.type !== 'pong') {
          onMessage(msg)
        }
      } catch {}
    }

    ws.current.onclose = () => {
      setConnected(false)
      // Auto-reconnect after 3 seconds
      setTimeout(connect, 3000)
    }

    ws.current.onerror = () => {
      ws.current?.close()
    }
  }, [onMessage])

  useEffect(() => {
    connect()
    return () => {
      ws.current?.close()
    }
  }, [])

  const sendPing = () => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send('ping')
    }
  }

  return { connected, sendPing }
}
