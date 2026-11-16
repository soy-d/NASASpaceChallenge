import { useEffect, useState } from 'react'

import { API } from '../api.js'

// Subscribes to the backend SSE stream. EventSource reconnects by itself.
export function useTelemetry() {
  const [snapshot, setSnapshot] = useState(null)
  const [status, setStatus] = useState('connecting') // connecting | live | reconnecting

  useEffect(() => {
    const es = new EventSource(`${API}/api/telemetry/stream`)
    es.addEventListener('telemetry', (e) => {
      try {
        setSnapshot(JSON.parse(e.data))
        setStatus('live')
      } catch (err) {
        console.error('Bad telemetry payload', err)
      }
    })
    es.onerror = () => setStatus('reconnecting')
    return () => es.close()
  }, [])

  return { snapshot, status }
}
