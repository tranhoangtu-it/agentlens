# Phase 2: Search, Filters & Pagination

## Context Links
- Server list endpoint: `server/main.py` L55-62 (already has `agent_name`, `limit`, `offset` params)
- Storage layer: `server/storage.py` L95-103 (`list_traces` with basic filtering)
- Dashboard list page: `dashboard/src/pages/traces-list-page.tsx`
- API client: `dashboard/src/lib/api-client.ts`

## Overview
- **Priority**: P1
- **Status**: pending
- **Effort**: 6h
- **Description**: Add full-text search, status/date/cost filters, and visible pagination controls to the trace list. Requires both server API expansion and dashboard UI.

## Key Insights
- Server already supports `agent_name`, `limit`, `offset` query params but dashboard never passes limit/offset
- SQLite FTS5 is available for full-text search but YAGNI — LIKE queries sufficient for <100K traces
- Dashboard has no filter UI at all; pagination shows count but no controls
- Need server to return `total` count for pagination math

## Requirements

### Functional
- **Search**: Text search by agent name (server-side, debounced 300ms)
- **Status filter**: Dropdown/toggle for completed/running/error
- **Date range filter**: Quick presets (1h, 24h, 7d, 30d) + custom range
- **Cost filter**: Min/max cost range
- **Pagination**: Page size selector (25/50/100), prev/next buttons, page indicator
- **URL state**: Filters persisted in URL hash params for shareability

### Non-Functional
- Search response <200ms for 10K traces
- Filter changes don't cause full page flash (smooth transitions)

## Architecture

### Server API Changes
Expand `GET /api/traces` query params:
```
GET /api/traces?
  q=search_text           # LIKE match on agent_name
  &status=completed       # exact match
  &from_date=2026-02-01   # ISO date, >= filter on created_at
  &to_date=2026-02-28     # ISO date, <= filter
  &min_cost=0.001         # >= filter on total_cost_usd
  &max_cost=1.0           # <= filter
  &limit=50               # page size
  &offset=0               # pagination offset
  &sort=created_at        # sort field
  &order=desc             # sort direction
```

Response schema change — add `total`:
```json
{
  "traces": [...],
  "total": 1234,
  "limit": 50,
  "offset": 0
}
```

### Dashboard Components
```
dashboard/src/
  components/
    trace-search-bar.tsx       # Search input + filter toggles
    trace-filter-controls.tsx  # Status, date, cost filter dropdowns
    pagination-controls.tsx    # Page navigation
  lib/
    api-client.ts              # Update fetchTraces with filter params
    use-trace-filters.ts       # Hook to manage filter state + URL sync
```

## Related Code Files

### Files to Modify
- `server/main.py` — expand `list_traces_endpoint` params
- `server/storage.py` — expand `list_traces` with new filters + total count
- `server/models.py` — add index on `status` field if not present
- `dashboard/src/lib/api-client.ts` — add filter params to `fetchTraces`
- `dashboard/src/pages/traces-list-page.tsx` — integrate filter bar + pagination
- `dashboard/src/components/trace-list-table.tsx` — remove inline empty state (move to page)

### Files to Create
- `dashboard/src/components/trace-search-bar.tsx`
- `dashboard/src/components/trace-filter-controls.tsx`
- `dashboard/src/components/pagination-controls.tsx`
- `dashboard/src/lib/use-trace-filters.ts`

## Implementation Steps

### Step 1: Server — expand storage layer
1. Update `list_traces()` in `storage.py`:
   - Add params: `q`, `status`, `from_date`, `to_date`, `min_cost`, `max_cost`, `sort`, `order`
   - Build dynamic WHERE clauses
   - Add separate COUNT query for total
   - Return `(traces, total)` tuple
2. Add index on `Trace.status` in `models.py`

### Step 2: Server — expand API endpoint
1. Update `list_traces_endpoint` in `main.py`:
   - Add new Query params matching above spec
   - Return `{"traces": [...], "total": N, "limit": L, "offset": O}`
2. Add input validation (date format, cost range)

### Step 3: Dashboard — filter state hook
1. Create `use-trace-filters.ts`:
   - State: `{ q, status, fromDate, toDate, minCost, maxCost, page, pageSize, sort, order }`
   - Sync to/from URL hash params
   - Expose `setFilter(key, value)`, `resetFilters()`, `filters` object
   - Auto-debounce `q` changes by 300ms

### Step 4: Dashboard — update API client
1. Update `fetchTraces()` to accept filter params object
2. Build query string from non-null filter values

### Step 5: Dashboard — search bar component
1. Create `trace-search-bar.tsx`:
   - Search icon + text input (using `ui/input`)
   - Clear button when text present
   - Debounced onChange

### Step 6: Dashboard — filter controls
1. Create `trace-filter-controls.tsx`:
   - Status filter: badge toggles (All / Completed / Running / Error)
   - Date quick-select: buttons (1h, 24h, 7d, 30d, All)
   - Cost range: two small inputs (min/max)
   - Reset all button

### Step 7: Dashboard — pagination controls
1. Create `pagination-controls.tsx`:
   - Page size selector (25/50/100)
   - "Showing X-Y of Z" text
   - Prev/Next buttons (disabled at bounds)
   - Page number display

### Step 8: Dashboard — integrate into list page
1. Update `traces-list-page.tsx`:
   - Add search bar above table
   - Add filter row below search
   - Add pagination below table
   - Wire all to `useTraceFilters` hook
   - Show skeleton loading during filter changes

## Todo List
- [ ] Add `status` index to `server/models.py`
- [ ] Expand `list_traces()` in `server/storage.py` with filters + total count
- [ ] Expand `list_traces_endpoint` in `server/main.py` with new query params
- [ ] Create `dashboard/src/lib/use-trace-filters.ts`
- [ ] Update `dashboard/src/lib/api-client.ts` with filter params
- [ ] Create `dashboard/src/components/trace-search-bar.tsx`
- [ ] Create `dashboard/src/components/trace-filter-controls.tsx`
- [ ] Create `dashboard/src/components/pagination-controls.tsx`
- [ ] Integrate filters + pagination into `traces-list-page.tsx`
- [ ] Test with 0, 1, 50, 1000+ traces
- [ ] Verify URL state persistence (reload page with filters = same results)

## Success Criteria
- Can search traces by agent name, results update within 300ms
- Can filter by status, date range, cost range
- Pagination shows correct totals and navigates properly
- Filters persist in URL hash — page reload preserves state
- Empty state shows "No traces match your filters" with reset button

## Risk Assessment
- **Risk**: SQLite LIKE queries slow at >50K traces — **Mitigation**: Add index on agent_name; FTS5 can be added later
- **Risk**: Too many filter params clutters URL — **Mitigation**: Only serialize non-default values

## Security Considerations
- Server-side SQL params use parameterized queries (SQLAlchemy handles this)
- Input validation on date format and numeric ranges prevents injection
