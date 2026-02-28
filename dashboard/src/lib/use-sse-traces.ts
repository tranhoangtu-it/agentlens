// Custom hook for SSE connection to /api/traces/stream — auto-reconnects on disconnect

import { useState, useEffect, useRef } from 'react'

export interface SSEEvent {
  type: string
  data: unknown
}

// Payload shapes for typed consumers
export interface SpanCreatedData {
  trace_id: string
  span: Record<string, unknown>
}

export interface TraceUpdatedData {
  trace_id: string
  status: string
  span_count: number
  total_cost_usd: number | null
  duration_ms: number | null
}

export interface UseSSETracesResult {
  /** Last event of any type — kept for backward compatibility */
  latestEvent: SSEEvent | null
  /** Latest span_created payload */
  latestSpanEvent: SpanCreatedData | null
  /** Latest trace_updated payload */
  latestTraceUpdate: TraceUpdatedData | null
  isConnected: boolean
}

const SSE_URL = '/api/traces/stream'
const RECONNECT_DELAY_MS = 3000

export function useSSETraces(): UseSSETracesResult {
  const [latestEvent, setLatestEvent] = useState<SSEEvent | null>(null)
  const [latestSpanEvent, setLatestSpanEvent] = useState<SpanCreatedData | null>(null)
  const [latestTraceUpdate, setLatestTraceUpdate] = useState<TraceUpdatedData | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let active = true

    function connect() {
      if (!active) return
      const es = new EventSource(SSE_URL)
      esRef.current = es

      es.onopen = () => { if (active) setIsConnected(true) }

      // Named SSE events require addEventListener (onmessage only fires for unnamed)
      const genericHandler = (e: MessageEvent) => {
        if (!active) return
        try {
          const data = JSON.parse(e.data as string)
          setLatestEvent({ type: e.type, data })
        } catch { /* ignore malformed */ }
      }

      const spanCreatedHandler = (e: MessageEvent) => {
        if (!active) return
        try {
          const data = JSON.parse(e.data as string) as SpanCreatedData
          setLatestSpanEvent(data)
          setLatestEvent({ type: 'span_created', data })
        } catch { /* ignore malformed */ }
      }

      const traceUpdatedHandler = (e: MessageEvent) => {
        if (!active) return
        try {
          const data = JSON.parse(e.data as string) as TraceUpdatedData
          setLatestTraceUpdate(data)
          setLatestEvent({ type: 'trace_updated', data })
        } catch { /* ignore malformed */ }
      }

      es.addEventListener('trace_created', genericHandler)
      es.addEventListener('span_created', spanCreatedHandler)
      es.addEventListener('trace_updated', traceUpdatedHandler)

      es.onerror = () => {
        es.close()
        esRef.current = null
        if (active) {
          setIsConnected(false)
          timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
        }
      }
    }

    connect()

    return () => {
      active = false
      esRef.current?.close()
      esRef.current = null
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  return { latestEvent, latestSpanEvent, latestTraceUpdate, isConnected }
}
