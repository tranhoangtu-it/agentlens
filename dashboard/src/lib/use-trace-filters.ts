// Hook to manage trace filter state with URL hash sync and debounced search

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { TraceFilters } from './api-client'

export interface FilterState {
  q: string
  status: string
  agent_name: string
  from_date: string
  to_date: string
  min_cost: string
  max_cost: string
  sort: string
  order: string
  page: number
  pageSize: number
}

const DEFAULTS: FilterState = {
  q: '',
  status: '',
  agent_name: '',
  from_date: '',
  to_date: '',
  min_cost: '',
  max_cost: '',
  sort: 'created_at',
  order: 'desc',
  page: 1,
  pageSize: 50,
}

// Parse URL hash params into FilterState (only non-default values are in hash)
function parseHash(): Partial<FilterState> {
  const hash = window.location.hash.slice(1)
  if (!hash) return {}
  const params = new URLSearchParams(hash)
  const out: Partial<FilterState> = {}
  for (const [key, val] of params.entries()) {
    if (key === 'page' || key === 'pageSize') {
      const n = parseInt(val, 10)
      if (!isNaN(n)) (out as Record<string, unknown>)[key] = n
    } else {
      (out as Record<string, unknown>)[key] = val
    }
  }
  return out
}

// Serialize non-default values to hash string
function toHash(state: FilterState): string {
  const params = new URLSearchParams()
  const stateMap = state as unknown as Record<string, unknown>
  for (const [key, def] of Object.entries(DEFAULTS)) {
    const val = stateMap[key]
    if (val !== def && val !== '') {
      params.set(key, String(val))
    }
  }
  const s = params.toString()
  return s ? `#${s}` : ''
}

export interface UseTraceFiltersReturn {
  filters: FilterState
  /** Debounced q for API calls (300ms) */
  debouncedQ: string
  setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  resetFilters: () => void
  /** Computed API params ready for fetchTraces() */
  apiParams: TraceFilters
}

export function useTraceFilters(): UseTraceFiltersReturn {
  const [filters, setFilters] = useState<FilterState>(() => ({
    ...DEFAULTS,
    ...parseHash(),
  }))
  const [debouncedQ, setDebouncedQ] = useState(filters.q)
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync state to URL hash whenever filters change
  useEffect(() => {
    const hash = toHash(filters)
    const current = window.location.hash || ''
    if (hash !== current) {
      history.replaceState(null, '', hash || window.location.pathname + window.location.search)
    }
  }, [filters])

  // Debounce search query
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      setDebouncedQ(filters.q)
    }, 300)
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current)
    }
  }, [filters.q])

  const setFilter = useCallback(<K extends keyof FilterState>(key: K, value: FilterState[K]) => {
    setFilters((prev) => {
      // Reset page to 1 when any non-page filter changes
      const resetPage = key !== 'page' && key !== 'pageSize' ? { page: 1 } : {}
      return { ...prev, [key]: value, ...resetPage }
    })
  }, [])

  const resetFilters = useCallback(() => {
    setFilters(DEFAULTS)
    setDebouncedQ('')
  }, [])

  // Build API params from current filter state
  const apiParams = useMemo((): TraceFilters => {
    const offset = (filters.page - 1) * filters.pageSize
    const p: TraceFilters = {
      limit: filters.pageSize,
      offset,
      sort: filters.sort,
      order: filters.order,
    }
    if (debouncedQ) p.q = debouncedQ
    if (filters.status) p.status = filters.status
    if (filters.agent_name) p.agent_name = filters.agent_name
    if (filters.from_date) p.from_date = filters.from_date
    if (filters.to_date) p.to_date = filters.to_date
    if (filters.min_cost !== '') p.min_cost = parseFloat(filters.min_cost)
    if (filters.max_cost !== '') p.max_cost = parseFloat(filters.max_cost)
    return p
  }, [filters, debouncedQ])

  return { filters, debouncedQ, setFilter, resetFilters, apiParams }
}
