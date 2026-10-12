import { useEffect, useRef, useState, useCallback } from 'react'
import { AgentEvent } from '@/lib/api'

export function useSSE(runId: string | null) {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!runId) return

    const es = new EventSource(`/api/runs/${runId}/events`)
    eventSourceRef.current = es

    es.onopen = () => {
      setIsConnected(true)
    }

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.agent) {
          setEvents(prev => [...prev, data as AgentEvent])
        }
      } catch (e) {
        console.error('Failed to parse SSE event:', e)
      }
    }

    es.onerror = () => {
      setIsConnected(false)
      es.close()
    }

    return () => {
      es.close()
      eventSourceRef.current = null
      setIsConnected(false)
    }
  }, [runId])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  return { events, isConnected, clearEvents }
}