# Phase 3: Real-Time Improvements

## Context Links
- SSE bus: `server/sse.py` (42 LOC, publishes `trace_created` only)
- SSE hook: `dashboard/src/lib/use-sse-traces.ts` (listens for `trace_created`)
- Topology graph: `dashboard/src/components/trace-topology-graph.tsx`
- Trace detail page: `dashboard/src/pages/trace-detail-page.tsx`

## Overview
- **Priority**: P1
- **Status**: pending
- **Effort**: 5h
- **Description**: Make the real-time experience feel alive: live-updating topology graph as spans arrive, animated running spans, SSE for span-level updates (not just trace-level), and auto-refresh on trace detail page.

## Key Insights
- Current SSE only fires `trace_created` event — no granular span updates
- SDK sends full trace on completion (fire-and-forget batch) — for true live streaming need incremental span reporting
- Topology graph is static after load; no re-fetch on SSE events
- Running spans show "running" text but no visual animation
- SSE bus is in-memory only (no persistence/replay) — fine for MVP

## Requirements

### Functional
- **Span-level SSE events**: Publish `span_started`, `span_ended`, `trace_updated` events
- **Incremental span ingestion**: New API endpoint `POST /api/traces/{id}/spans` for adding spans to existing trace
- **Live topology graph**: Auto-adds new nodes/edges when spans arrive via SSE
- **Running span animation**: Pulsing border/glow on nodes that haven't ended yet
- **Auto-refresh detail page**: When SSE `trace_updated` fires for current trace, re-fetch
- **Connection status**: Visual indicator in header (already exists, enhance)

### Non-Functional
- SSE reconnection within 3s (already implemented)
- No perceptible lag between SDK span send and graph node appearing
- Animations should be CSS-only (no JS animation loops)

## Architecture

### Server Changes
```
POST /api/traces/{trace_id}/spans   # Incremental span ingestion
  Body: { "spans": [SpanIn, ...] }
  Publishes: "span_created" SSE event per span
  Publishes: "trace_updated" SSE event with aggregates
```

SSE event types:
```
event: trace_created    # New trace started
data: {"trace_id": "...", "agent_name": "..."}

event: trace_updated    # Trace aggregates changed
data: {"trace_id": "...", "status": "...", "span_count": N, "total_cost_usd": ...}

event: span_created     # New span added to existing trace
data: {"trace_id": "...", "span": {...}}
```

### Dashboard Changes
```
dashboard/src/
  lib/
    use-sse-traces.ts          # Add span_created, trace_updated listeners
    use-live-trace-detail.ts   # Hook for auto-refreshing trace detail
  components/
    trace-topology-graph.tsx   # Animate running nodes, react to new spans
```

## Related Code Files

### Files to Modify
- `server/main.py` — add `POST /api/traces/{trace_id}/spans` endpoint
- `server/storage.py` — add `add_spans_to_trace()` function, `update_trace_aggregates()`
- `server/sse.py` — add `span_created` and `trace_updated` event publishing
- `dashboard/src/lib/use-sse-traces.ts` — listen for new event types
- `dashboard/src/components/trace-topology-graph.tsx` — running node animation, live updates
- `dashboard/src/pages/trace-detail-page.tsx` — auto-refresh on `trace_updated`

### Files to Create
- `dashboard/src/lib/use-live-trace-detail.ts` — hook combining fetch + SSE for live trace
- `sdk/agentlens/transport.py` — add incremental span posting (optional enhancement)

## Implementation Steps

### Step 1: Server — incremental span ingestion
1. Add `add_spans_to_trace(trace_id, spans_data)` to `storage.py`:
   - Insert new spans for existing trace
   - Recalculate aggregates (cost, tokens, duration, status, span_count)
   - Return updated trace
2. Add `POST /api/traces/{trace_id}/spans` to `main.py`:
   - Accept `{"spans": [SpanIn, ...]}` body
   - Call `add_spans_to_trace()`
   - Publish SSE events

### Step 2: Server — granular SSE events
1. Update `ingest_trace()` in `main.py` to also publish `span_created` for each span
2. Update incremental endpoint to publish:
   - `span_created` per span with full span data
   - `trace_updated` with updated trace aggregates
3. Keep `trace_created` for new traces (backward compatible)

### Step 3: Dashboard — enhanced SSE hook
1. Update `use-sse-traces.ts`:
   - Add `addEventListener` for `span_created`, `trace_updated`
   - Expose `latestSpanEvent` and `latestTraceUpdate` separately
   - Keep existing `latestEvent` for backward compatibility

### Step 4: Dashboard — live trace detail hook
1. Create `use-live-trace-detail.ts`:
   - Initial fetch of trace + spans
   - Subscribe to SSE `span_created` events filtered by current trace_id
   - Merge new spans into local state without full re-fetch
   - Re-fetch on `trace_updated` for aggregate changes
   - Return `{ trace, spans, loading, isLive }`

### Step 5: Dashboard — running span animation
1. Update `trace-topology-graph.tsx`:
   - Add CSS animation for running nodes (no `end_ms`):
     ```css
     @keyframes pulse-ring {
       0% { box-shadow: 0 0 0 0 rgba(var(--color), 0.4); }
       70% { box-shadow: 0 0 0 6px rgba(var(--color), 0); }
       100% { box-shadow: 0 0 0 0 rgba(var(--color), 0); }
     }
     ```
   - Apply to nodes where `end_ms === null`
   - Add animated dashed edges for running connections

### Step 6: Dashboard — integrate live updates into detail page
1. Update `trace-detail-page.tsx`:
   - Replace `fetchTrace` with `useLiveTraceDetail` hook
   - Topology graph automatically updates when new spans arrive
   - Add "Live" indicator when trace status is "running"
   - Show span count incrementing in real-time

### Step 7: SDK — optional incremental transport
1. Add `post_spans(trace_id, spans)` to `transport.py`:
   - POST to `/api/traces/{trace_id}/spans`
   - Same fire-and-forget pattern
2. Update `ActiveTrace.flush()` to optionally use incremental mode
   - Default: batch mode (current behavior, backward compatible)
   - Optional: `agentlens.configure(streaming=True)` for span-by-span reporting

## Todo List
- [ ] Add `add_spans_to_trace()` to `server/storage.py`
- [ ] Add `POST /api/traces/{trace_id}/spans` to `server/main.py`
- [ ] Update SSE bus to publish `span_created` and `trace_updated` events
- [ ] Update `use-sse-traces.ts` with new event listeners
- [ ] Create `use-live-trace-detail.ts` hook
- [ ] Add CSS pulse animation for running nodes in topology graph
- [ ] Add animated dashed edges for running connections
- [ ] Integrate live updates into `trace-detail-page.tsx`
- [ ] Add `post_spans()` to SDK transport (optional)
- [ ] Test with simulated slow agent (spans arriving 1-2s apart)

## Success Criteria
- Opening a running trace shows nodes appearing in real-time
- Running nodes have visible pulsing animation
- Trace aggregates (cost, duration, span count) update live
- No flicker or layout jumps when new spans appear
- Works with both batch and incremental SDK transport

## Risk Assessment
- **Risk**: Frequent SSE events cause React re-render thrashing — **Mitigation**: Batch state updates, use `useRef` for intermediate state
- **Risk**: Concurrent span insertions cause SQLite contention — **Mitigation**: WAL mode already enabled; upsert pattern handles duplicates
- **Risk**: Live topology graph layout jumps when dagre re-computes — **Mitigation**: Use incremental layout (only position new nodes) or animate transitions

## Security Considerations
- Validate `trace_id` exists before accepting spans
- Rate limit span ingestion endpoint (max 100 spans/request)
