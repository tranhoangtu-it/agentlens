// Hook combining initial fetch + SSE for live-updating trace detail

import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchTrace, type Trace, type Span } from './api-client'
import { useSSETraces } from './use-sse-traces'

interface UseLiveTraceDetailResult {
  trace: Trace | null
  spans: Span[]
  loading: boolean
  error: string | null
  /** true when SSE is connected and trace.status === 'running' */
  isLive: boolean
}

export function useLiveTraceDetail(traceId: string): UseLiveTraceDetailResult {
  const [trace, setTrace] = useState<Trace | null>(null)
  const [spans, setSpans] = useState<Span[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { latestSpanEvent, latestTraceUpdate, isConnected } = useSSETraces()

  // Track span IDs already in state to avoid duplicates
  const knownSpanIds = useRef<Set<string>>(new Set())

  const loadTrace = useCallback(async () => {
    try {
      const res = await fetchTrace(traceId)
      setTrace(res.trace)
      setSpans(res.spans)
      knownSpanIds.current = new Set(res.spans.map((s) => s.id))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load trace')
    } finally {
      setLoading(false)
    }
  }, [traceId])

  // Initial fetch
  useEffect(() => {
    setLoading(true)
    knownSpanIds.current = new Set()
    void loadTrace()
  }, [loadTrace])

  // Merge incoming span_created events for this trace
  useEffect(() => {
    if (!latestSpanEvent || latestSpanEvent.trace_id !== traceId) return
    const incoming = latestSpanEvent.span as unknown as Span
    if (!incoming?.id || knownSpanIds.current.has(incoming.id)) return
    knownSpanIds.current.add(incoming.id)
    setSpans((prev) => [...prev, incoming])
  }, [latestSpanEvent, traceId])

  // Re-fetch aggregates when trace_updated fires for this trace
  useEffect(() => {
    if (!latestTraceUpdate || latestTraceUpdate.trace_id !== traceId) return
    // Update trace aggregates in-place without a full round-trip
    setTrace((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        status: latestTraceUpdate.status as Trace['status'],
        span_count: latestTraceUpdate.span_count,
        total_cost_usd: latestTraceUpdate.total_cost_usd ?? prev.total_cost_usd,
        duration_ms: latestTraceUpdate.duration_ms ?? prev.duration_ms,
      }
    })
  }, [latestTraceUpdate, traceId])

  const isLive = isConnected && trace?.status === 'running'

  return { trace, spans, loading, error, isLive }
}
