// Alerts list page — shows fired alert events with resolve action

import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react'
import { fetchAlerts, resolveAlert, type AlertEvent } from '../lib/alert-api-client'
import { cn } from '../lib/utils'

export function AlertsListPage({ onNavigateTrace }: { onNavigateTrace: (id: string) => void }) {
  const [alerts, setAlerts] = useState<AlertEvent[]>([])
  const [total, setTotal] = useState(0)
  const [showResolved, setShowResolved] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchAlerts({ resolved: showResolved ? undefined : false, limit: 100 })
      setAlerts(res.alerts)
      setTotal(res.total)
    } catch { /* ignore */ }
    setLoading(false)
  }, [showResolved])

  useEffect(() => { load() }, [load])

  async function handleResolve(id: string) {
    try {
      await resolveAlert(id)
      load()
    } catch { /* ignore */ }
  }

  const metricBadge: Record<string, string> = {
    cost: 'bg-yellow-500/20 text-yellow-400',
    error_rate: 'bg-red-500/20 text-red-400',
    latency: 'bg-blue-500/20 text-blue-400',
    missing_span: 'bg-purple-500/20 text-purple-400',
  }

  return (
    <div className="flex-1 overflow-auto p-5">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold">Alerts ({total})</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={showResolved}
              onChange={(e) => setShowResolved(e.target.checked)}
              className="rounded"
            />
            Show resolved
          </label>
          <button onClick={load} className="p-1.5 hover:bg-muted rounded-md transition-colors">
            <RefreshCw size={14} className={cn(loading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="text-center text-muted-foreground text-sm py-12">
          {loading ? 'Loading...' : 'No alerts found'}
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={cn(
                'border rounded-lg p-3 flex items-start gap-3 transition-colors',
                a.resolved ? 'border-border/50 opacity-60' : 'border-border',
              )}
            >
              {a.resolved ? (
                <CheckCircle size={16} className="text-green-400 mt-0.5 shrink-0" />
              ) : (
                <AlertTriangle size={16} className="text-yellow-400 mt-0.5 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn('text-xs px-1.5 py-0.5 rounded font-medium', metricBadge[a.metric] ?? 'bg-muted text-muted-foreground')}>
                    {a.metric}
                  </span>
                  <span className="text-xs text-muted-foreground">{a.agent_name}</span>
                  <span className="text-xs text-muted-foreground/60">
                    {new Date(a.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-sm">{a.message}</p>
                <button
                  onClick={() => onNavigateTrace(a.trace_id)}
                  className="text-xs text-primary hover:underline mt-1"
                >
                  View trace {a.trace_id.slice(0, 8)}...
                </button>
              </div>
              {!a.resolved && (
                <button
                  onClick={() => handleResolve(a.id)}
                  className="text-xs px-2 py-1 bg-muted hover:bg-muted/80 rounded transition-colors shrink-0"
                >
                  Resolve
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
