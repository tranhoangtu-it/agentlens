# Phase 4: Trace Comparison / Diff

## Context Links
- Trace detail API: `server/main.py` L80-85 (`GET /api/traces/{trace_id}`)
- Topology graph: `dashboard/src/components/trace-topology-graph.tsx`
- Span detail panel: `dashboard/src/components/span-detail-panel.tsx`
- API client: `dashboard/src/lib/api-client.ts`

## Overview
- **Priority**: P2
- **Status**: pending
- **Effort**: 6h
- **Depends on**: Phase 1 (UI primitives), Phase 2 (trace selection UX)
- **Description**: Side-by-side comparison of two agent runs. Shows topology graphs side-by-side, highlights structural differences (added/removed/changed spans), and diffs span input/output.

## Key Insights
- Trace comparison is a killer feature for debugging agent regressions ("why did run B cost 3x more than run A?")
- Structural diff = compare span trees by name+type; data diff = compare input/output per matched span
- Spans don't have stable IDs across runs — match by `name` + `type` + position in tree
- Keep it simple: two-panel layout, color-coded differences, no complex merge algorithms

## Requirements

### Functional
- Select two traces for comparison from trace list (checkbox or "Compare" button)
- Side-by-side topology graphs with synchronized zoom/pan
- Color-coded span matching:
  - Green = span exists in both, data matches
  - Yellow = span exists in both, data differs
  - Red = span only in left trace
  - Blue = span only in right trace
- Click matched span pair to see input/output diff
- Summary stats: cost diff, duration diff, span count diff, token diff
- Deep link: `#/compare/{traceA}/{traceB}`

### Non-Functional
- Comparison loads in <500ms for traces with <200 spans each
- Responsive at 1440px+ width (each panel gets ~700px)

## Architecture

### Server Changes
New endpoint:
```
GET /api/traces/compare?left={id}&right={id}
Response: {
  left: { trace: Trace, spans: Span[] },
  right: { trace: Trace, spans: Span[] },
  diff: {
    matched: [{ left_span_id, right_span_id, status: "identical"|"changed" }],
    left_only: [span_id, ...],
    right_only: [span_id, ...]
  }
}
```

Diff algorithm (server-side for consistency):
1. Build span trees for both traces (parent_id -> children)
2. Match spans by `(name, type, depth, sibling_index)` tuple
3. For matched pairs, compare `input` + `output` fields
4. Return categorized matches

### Dashboard Components
```
dashboard/src/
  pages/
    trace-compare-page.tsx      # Main comparison page
  components/
    trace-compare-header.tsx    # Stats diff summary bar
    trace-compare-graphs.tsx    # Two synced topology graphs
    span-diff-panel.tsx         # Input/output diff for matched span pair
  lib/
    api-client.ts               # Add fetchTraceComparison()
    diff-utils.ts               # Client-side diff highlighting for text
```

### Routing
Add to `App.tsx` hash router:
```
#/compare/{leftId}/{rightId}  -> TraceComparePage
```

## Related Code Files

### Files to Modify
- `server/main.py` — add `GET /api/traces/compare` endpoint
- `server/storage.py` — add `compare_traces()` function with diff logic
- `dashboard/src/App.tsx` — add compare route
- `dashboard/src/lib/api-client.ts` — add `fetchTraceComparison()`
- `dashboard/src/pages/traces-list-page.tsx` — add compare selection UI
- `dashboard/src/components/trace-list-table.tsx` — add checkbox column + compare button

### Files to Create
- `server/diff.py` — span tree diff algorithm
- `dashboard/src/pages/trace-compare-page.tsx`
- `dashboard/src/components/trace-compare-header.tsx`
- `dashboard/src/components/trace-compare-graphs.tsx`
- `dashboard/src/components/span-diff-panel.tsx`
- `dashboard/src/lib/diff-utils.ts`

## Implementation Steps

### Step 1: Server — diff algorithm
1. Create `server/diff.py`:
   - `build_span_tree(spans)` — convert flat list to nested tree
   - `match_spans(left_tree, right_tree)` — recursive matching by name+type+position
   - `compute_diff(left_spans, right_spans)` — return matched, left_only, right_only
   - For matched pairs: compare input/output, mark as "identical" or "changed"

### Step 2: Server — compare endpoint
1. Add `GET /api/traces/compare` to `main.py`:
   - Query params: `left`, `right` (trace IDs)
   - Fetch both traces + spans
   - Run diff algorithm
   - Return combined response

### Step 3: Dashboard — API client + diff utilities
1. Add `fetchTraceComparison(leftId, rightId)` to `api-client.ts`
2. Create `diff-utils.ts`:
   - Simple line-by-line text diff for input/output comparison
   - Return array of `{ type: 'added'|'removed'|'unchanged', text }` segments
   - Keep simple: split by newline, compare lines (no Myers diff needed)

### Step 4: Dashboard — trace selection in list page
1. Update `trace-list-table.tsx`:
   - Add checkbox column (only visible when compare mode active)
   - Add "Compare" button in header that activates compare mode
   - When 2 traces selected, show "Compare Selected" action button
   - Navigate to `#/compare/{leftId}/{rightId}`

### Step 5: Dashboard — compare page layout
1. Create `trace-compare-page.tsx`:
   - Fetch comparison data
   - Two-column layout with synced scroll
   - Header showing diff summary stats
   - Click span pair to open diff panel

### Step 6: Dashboard — side-by-side graphs
1. Create `trace-compare-graphs.tsx`:
   - Two `TraceTopologyGraph` instances side by side
   - Color nodes based on diff status (matched/changed/only-left/only-right)
   - Synchronized zoom/pan (link React Flow viewport state)
   - Highlight corresponding span in other graph on hover

### Step 7: Dashboard — span diff panel
1. Create `span-diff-panel.tsx`:
   - Shows when a matched span pair is clicked
   - Two-column layout: left span data | right span data
   - Highlight text differences in input/output
   - Show cost/duration/token diffs with arrows (e.g., "$0.02 -> $0.06 (+200%)")

### Step 8: Dashboard — routing
1. Update `App.tsx`:
   - Add `compare` route: `{ name: 'compare', leftId, rightId }`
   - Parse `#/compare/{left}/{right}` from hash

## Todo List
- [ ] Create `server/diff.py` with span tree diff algorithm
- [ ] Add `GET /api/traces/compare` endpoint to `server/main.py`
- [ ] Add `fetchTraceComparison()` to `dashboard/src/lib/api-client.ts`
- [ ] Create `dashboard/src/lib/diff-utils.ts`
- [ ] Add checkbox selection + compare button to trace list table
- [ ] Create `dashboard/src/pages/trace-compare-page.tsx`
- [ ] Create `dashboard/src/components/trace-compare-header.tsx`
- [ ] Create `dashboard/src/components/trace-compare-graphs.tsx`
- [ ] Create `dashboard/src/components/span-diff-panel.tsx`
- [ ] Add compare route to `App.tsx`
- [ ] Test with identical traces, different traces, traces with different span counts
- [ ] Test with traces from different agents (structural mismatch)

## Success Criteria
- Can select any two traces and see side-by-side comparison
- Color coding clearly shows which spans match/differ/are unique
- Can drill into matched span pair and see input/output diff
- Summary stats show cost/duration/token differences at a glance
- Deep link works (share comparison URL)

## Risk Assessment
- **Risk**: Span matching produces false positives when agents have duplicate span names — **Mitigation**: Use (name, type, depth, sibling_index) tuple, not just name
- **Risk**: Large traces (100+ spans) make side-by-side graphs hard to read — **Mitigation**: Add collapse/expand on subtrees, minimap navigation
- **Risk**: Text diff on large input/output is slow — **Mitigation**: Truncate to first 4KB, lazy-load full diff

## Security Considerations
- Both trace IDs validated before comparison
- No cross-user data exposure (single-tenant, no auth)
