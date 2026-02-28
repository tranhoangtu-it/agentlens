// Alert rules management page — create, edit, toggle, delete rules

import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, RefreshCw } from 'lucide-react'
import {
  fetchAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  type AlertRule,
  type AlertRuleIn,
} from '../lib/alert-api-client'
import { cn } from '../lib/utils'

const METRICS = ['cost', 'error_rate', 'latency', 'missing_span'] as const
const OPERATORS = ['gt', 'lt', 'gte', 'lte'] as const
const OP_LABELS: Record<string, string> = { gt: '>', lt: '<', gte: '>=', lte: '<=' }

function emptyRule(): AlertRuleIn {
  return { name: '', agent_name: '*', metric: 'cost', operator: 'gt', threshold: 0, mode: 'absolute', window_size: 10 }
}

export function AlertRulesPage() {
  const [rules, setRules] = useState<AlertRule[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<AlertRuleIn>(emptyRule())
  const [editId, setEditId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchAlertRules()
      setRules(res.rules)
    } catch { /* ignore */ }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      if (editId) {
        await updateAlertRule(editId, form)
      } else {
        await createAlertRule(form)
      }
      setShowForm(false)
      setEditId(null)
      setForm(emptyRule())
      load()
    } catch { /* ignore */ }
  }

  async function handleDelete(id: string) {
    try {
      await deleteAlertRule(id)
      load()
    } catch { /* ignore */ }
  }

  async function handleToggle(rule: AlertRule) {
    try {
      await updateAlertRule(rule.id, { enabled: !rule.enabled })
      load()
    } catch { /* ignore */ }
  }

  function startEdit(rule: AlertRule) {
    setForm({
      name: rule.name,
      agent_name: rule.agent_name,
      metric: rule.metric,
      operator: rule.operator,
      threshold: rule.threshold,
      mode: rule.mode,
      window_size: rule.window_size,
      webhook_url: rule.webhook_url,
    })
    setEditId(rule.id)
    setShowForm(true)
  }

  return (
    <div className="flex-1 overflow-auto p-5">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold">Alert Rules ({rules.length})</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setShowForm(!showForm); setEditId(null); setForm(emptyRule()) }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90 transition-colors"
          >
            <Plus size={14} /> New Rule
          </button>
          <button onClick={load} className="p-1.5 hover:bg-muted rounded-md transition-colors">
            <RefreshCw size={14} className={cn(loading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Create/Edit form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="border rounded-lg p-4 mb-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Rule name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required
              className="px-3 py-1.5 bg-muted rounded-md text-sm border border-border" />
            <input placeholder="Agent name (* = all)" value={form.agent_name} onChange={(e) => setForm({ ...form, agent_name: e.target.value })} required
              className="px-3 py-1.5 bg-muted rounded-md text-sm border border-border" />
            <select value={form.metric} onChange={(e) => setForm({ ...form, metric: e.target.value })}
              className="px-3 py-1.5 bg-muted rounded-md text-sm border border-border">
              {METRICS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <select value={form.operator} onChange={(e) => setForm({ ...form, operator: e.target.value })}
              className="px-3 py-1.5 bg-muted rounded-md text-sm border border-border">
              {OPERATORS.map((o) => <option key={o} value={o}>{OP_LABELS[o]} ({o})</option>)}
            </select>
            <input type="number" step="any" placeholder="Threshold" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })} required
              className="px-3 py-1.5 bg-muted rounded-md text-sm border border-border" />
            <select value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}
              className="px-3 py-1.5 bg-muted rounded-md text-sm border border-border">
              <option value="absolute">Absolute</option>
              <option value="relative">Relative (multiplier)</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-sm">
              {editId ? 'Update' : 'Create'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditId(null) }}
              className="px-3 py-1.5 bg-muted rounded-md text-sm">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Rules list */}
      {rules.length === 0 ? (
        <div className="text-center text-muted-foreground text-sm py-12">
          {loading ? 'Loading...' : 'No alert rules configured'}
        </div>
      ) : (
        <div className="space-y-2">
          {rules.map((r) => (
            <div key={r.id} className={cn('border rounded-lg p-3 flex items-center gap-3', !r.enabled && 'opacity-50')}>
              <button onClick={() => handleToggle(r)}
                className={cn('w-8 h-4 rounded-full transition-colors relative shrink-0',
                  r.enabled ? 'bg-primary' : 'bg-muted-foreground/30')}>
                <span className={cn('absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform',
                  r.enabled ? 'left-4' : 'left-0.5')} />
              </button>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{r.name}</span>
                  <span className="text-xs text-muted-foreground">{r.agent_name}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {r.metric} {OP_LABELS[r.operator]} {r.threshold} ({r.mode}, window: {r.window_size})
                </p>
              </div>
              <button onClick={() => startEdit(r)} className="text-xs px-2 py-1 hover:bg-muted rounded transition-colors">
                Edit
              </button>
              <button onClick={() => handleDelete(r.id)} className="p-1 hover:bg-red-500/20 rounded transition-colors">
                <Trash2 size={14} className="text-red-400" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
