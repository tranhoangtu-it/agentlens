// Filter controls for trace list — status badges, date presets, agent dropdown, cost range

import type { FilterState } from '../lib/use-trace-filters'

interface Props {
  filters: FilterState
  agents: string[]
  onFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  onReset: () => void
}

const STATUSES = ['completed', 'running', 'error'] as const

// Date quick-select presets — compute ISO from_date relative to now
const DATE_PRESETS: { label: string; hours: number | null }[] = [
  { label: '1h', hours: 1 },
  { label: '24h', hours: 24 },
  { label: '7d', hours: 24 * 7 },
  { label: '30d', hours: 24 * 30 },
  { label: 'All', hours: null },
]

function fromDateForHours(hours: number): string {
  const d = new Date(Date.now() - hours * 3600 * 1000)
  // ISO date string in YYYY-MM-DDTHH:mm:ss (local-neutral, server accepts ISO)
  return d.toISOString().slice(0, 19)
}

function activePreset(fromDate: string): string | null {
  if (!fromDate) return 'All'
  for (const p of DATE_PRESETS) {
    if (p.hours === null) continue
    const expected = fromDateForHours(p.hours)
    // Allow ±5s tolerance for rendering lag
    const diff = Math.abs(new Date(expected).getTime() - new Date(fromDate).getTime())
    if (diff < 10_000) return p.label
  }
  return null
}

// Check if any filter deviates from default
function hasActiveFilters(filters: FilterState): boolean {
  return (
    !!filters.q ||
    !!filters.status ||
    !!filters.agent_name ||
    !!filters.from_date ||
    !!filters.to_date ||
    !!filters.min_cost ||
    !!filters.max_cost
  )
}

export function TraceFilterControls({ filters, agents, onFilter, onReset }: Props) {
  const currentPreset = activePreset(filters.from_date)

  function handleDatePreset(hours: number | null) {
    if (hours === null) {
      onFilter('from_date', '')
      onFilter('to_date', '')
    } else {
      onFilter('from_date', fromDateForHours(hours))
      onFilter('to_date', '')
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      {/* Status filter badges */}
      <div className="flex items-center gap-1">
        <span className="text-gray-500 text-xs mr-1">Status</span>
        <button
          onClick={() => onFilter('status', '')}
          className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
            !filters.status
              ? 'bg-gray-600 border-gray-500 text-white'
              : 'border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300'
          }`}
        >
          All
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => onFilter('status', filters.status === s ? '' : s)}
            className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
              filters.status === s
                ? s === 'completed'
                  ? 'bg-green-500/20 border-green-500/60 text-green-400'
                  : s === 'running'
                  ? 'bg-yellow-500/20 border-yellow-500/60 text-yellow-400'
                  : 'bg-red-500/20 border-red-500/60 text-red-400'
                : 'border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Date quick-select */}
      <div className="flex items-center gap-1">
        <span className="text-gray-500 text-xs mr-1">Date</span>
        {DATE_PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => handleDatePreset(p.hours)}
            className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
              currentPreset === p.label
                ? 'bg-blue-500/20 border-blue-500/60 text-blue-400'
                : 'border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Agent dropdown — only shown when there are known agents */}
      {agents.length > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500 text-xs">Agent</span>
          <select
            value={filters.agent_name}
            onChange={(e) => onFilter('agent_name', e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1
                       focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
          >
            <option value="">All agents</option>
            {agents.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
      )}

      {/* Cost range */}
      <div className="flex items-center gap-1.5">
        <span className="text-gray-500 text-xs">Cost</span>
        <input
          type="number"
          min={0}
          step="0.0001"
          placeholder="min $"
          value={filters.min_cost}
          onChange={(e) => onFilter('min_cost', e.target.value)}
          className="w-20 bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1
                     focus:outline-none focus:border-blue-500 transition-colors placeholder-gray-600"
        />
        <span className="text-gray-600">–</span>
        <input
          type="number"
          min={0}
          step="0.0001"
          placeholder="max $"
          value={filters.max_cost}
          onChange={(e) => onFilter('max_cost', e.target.value)}
          className="w-20 bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1
                     focus:outline-none focus:border-blue-500 transition-colors placeholder-gray-600"
        />
      </div>

      {/* Reset button — only shown when filters are active */}
      {hasActiveFilters(filters) && (
        <button
          onClick={onReset}
          className="ml-auto flex items-center gap-1 px-2.5 py-1 rounded text-xs
                     text-gray-400 border border-gray-700 hover:border-gray-500 hover:text-gray-200
                     transition-colors"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Reset filters
        </button>
      )}
    </div>
  )
}
