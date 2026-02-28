# Phase 7: Performance & Scale

## Context Links
- Storage layer: `server/storage.py` (114 LOC, SQLite with WAL)
- Trace list page: `dashboard/src/pages/traces-list-page.tsx`
- Topology graph: `dashboard/src/components/trace-topology-graph.tsx`
- Server models: `server/models.py` (indexes on id, agent_name, created_at)

## Overview
- **Priority**: P3
- **Status**: pending
- **Effort**: 2h
- **Depends on**: All feature phases
- **Description**: Optimize for 10K+ traces. Server-side: add database indexes, query optimization, response caching. Dashboard: virtualized table, lazy loading, memoization.

## Key Insights
- SQLite is surprisingly capable: handles 10K+ rows fine with proper indexes and WAL mode (already enabled)
- Main bottleneck will be dashboard: rendering 10K table rows, large topology graphs
- React Flow handles ~500 nodes well; beyond that need virtualization or collapse
- Current trace list fetches all traces at once (no pagination in practice)
- Phase 2 pagination solves most scale issues; this phase optimizes the edges

## Requirements

### Functional
- Trace list page handles 10K+ traces without UI lag
- Topology graph handles 200+ span traces without degradation
- API response time <100ms for filtered queries on 50K traces
- Dashboard initial load <2s (TTI)

### Non-Functional
- No new infrastructure (keep SQLite, no Redis/Postgres)
- Backward compatible with existing data

## Architecture

### Server Optimizations
1. **Database indexes** — add missing compound indexes
2. **Response compression** — enable gzip for JSON responses
3. **Query optimization** — avoid N+1 queries, use eager loading
4. **Connection pooling** — configure SQLAlchemy pool

### Dashboard Optimizations
1. **Virtualized table** — render only visible rows (react-virtual)
2. **Memoized components** — React.memo on expensive renders
3. **Lazy code splitting** — dynamic import for compare page
4. **Bundle optimization** — tree-shake unused Recharts/React Flow code

## Related Code Files

### Files to Modify
- `server/storage.py` — add indexes, optimize queries
- `server/main.py` — add gzip middleware, optimize response serialization
- `server/models.py` — add compound indexes
- `dashboard/src/components/trace-list-table.tsx` — add virtualization
- `dashboard/src/components/trace-topology-graph.tsx` — optimize for large graphs
- `dashboard/src/App.tsx` — lazy load compare page
- `dashboard/vite.config.ts` — bundle optimization

### Files to Create
- None (optimizations to existing files)

## Implementation Steps

### Step 1: Database indexes
1. Add compound indexes in `models.py`:
   ```python
   class Trace(SQLModel, table=True):
       # ... existing fields
       class Config:
           # Compound index for common filter queries
           pass
   ```
2. Add via SQLAlchemy `Index()`:
   - `ix_trace_status_created` on (status, created_at)
   - `ix_trace_agent_created` on (agent_name, created_at)
   - `ix_trace_cost` on (total_cost_usd)

### Step 2: Server response compression
1. Add GZip middleware to `main.py`:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```

### Step 3: Optimize storage queries
1. In `list_traces()`:
   - Use `select(Trace).options(load_only(...))` to exclude unused columns from list
   - Ensure COUNT query uses index-only scan
2. In `get_trace()`:
   - Single query with join instead of two queries
   - Or keep two queries but ensure span query uses trace_id index

### Step 4: Dashboard virtualized table
1. Install `@tanstack/react-virtual` (lightweight, no full table library needed)
2. Update `trace-list-table.tsx`:
   - Wrap table body in virtualizer
   - Only render visible rows + overscan buffer
   - Keep header sticky

### Step 5: Dashboard memoization
1. Wrap expensive components with `React.memo`:
   - `TraceTopologyGraph` — only re-render when spans/selectedSpanId change
   - `CostSummaryChart` — only re-render when spans change
   - `SpanDetailPanel` — only re-render when span changes
2. Use `useMemo` for dagre layout computation (already done)
3. Use `useCallback` for event handlers (partially done)

### Step 6: Large graph optimization
1. In `trace-topology-graph.tsx`:
   - For traces with >100 spans: auto-collapse subtrees beyond depth 3
   - Add expand/collapse toggle on parent nodes
   - Show span count badge on collapsed nodes
   - Lazy render: only compute positions for visible viewport area

### Step 7: Bundle optimization
1. Update `vite.config.ts`:
   ```ts
   build: {
     rollupOptions: {
       output: {
         manualChunks: {
           'react-flow': ['@xyflow/react'],
           'recharts': ['recharts'],
         }
       }
     }
   }
   ```
2. Lazy load compare page:
   ```tsx
   const TraceComparePage = lazy(() => import('./pages/trace-compare-page'))
   ```

## Todo List
- [ ] Add compound database indexes to `server/models.py`
- [ ] Add GZip middleware to `server/main.py`
- [ ] Optimize `list_traces()` query in `server/storage.py`
- [ ] Add `@tanstack/react-virtual` for virtualized table
- [ ] Apply `React.memo` to expensive dashboard components
- [ ] Add subtree collapse for large topology graphs
- [ ] Configure Vite manual chunks for code splitting
- [ ] Lazy load compare page
- [ ] Benchmark: seed 10K traces, measure list page load time
- [ ] Benchmark: seed 200-span trace, measure detail page render

## Success Criteria
- Trace list page renders 10K traces without jank (60fps scroll)
- API response for filtered query on 50K traces <100ms
- 200-span topology graph renders in <1s
- Dashboard bundle size <500KB gzipped
- Lighthouse performance score >90

## Risk Assessment
- **Risk**: Virtualized table breaks existing CSS layout — **Mitigation**: Use CSS Grid with fixed row heights
- **Risk**: Subtree collapse loses context for users — **Mitigation**: Show collapsed span count, expand on click

## Security Considerations
- GZip compression: no security implications for internal tool
- No new attack surface
