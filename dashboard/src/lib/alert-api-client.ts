// API client for alert rules and alert events

import { fetchWithAuth } from './fetch-with-auth'

const BASE = '/api'

export interface AlertRule {
  id: string
  name: string
  agent_name: string
  metric: 'cost' | 'error_rate' | 'latency' | 'missing_span'
  operator: 'gt' | 'lt' | 'gte' | 'lte'
  threshold: number
  mode: 'absolute' | 'relative'
  window_size: number
  enabled: boolean
  webhook_url: string | null
  created_at: string
  updated_at: string
}

export interface AlertEvent {
  id: string
  rule_id: string
  trace_id: string
  agent_name: string
  metric: string
  value: number
  threshold: number
  message: string
  resolved: boolean
  created_at: string
}

export interface AlertRuleIn {
  name: string
  agent_name: string
  metric: string
  operator?: string
  threshold: number
  mode?: string
  window_size?: number
  enabled?: boolean
  webhook_url?: string | null
}

export interface AlertsResponse {
  alerts: AlertEvent[]
  total: number
  limit: number
  offset: number
}

// ── Alert Rules ─────────────────────────────────────────────────────────────

export async function fetchAlertRules(
  params?: { agent_name?: string; metric?: string; enabled?: boolean },
): Promise<{ rules: AlertRule[] }> {
  const qs = new URLSearchParams()
  if (params?.agent_name) qs.set('agent_name', params.agent_name)
  if (params?.metric) qs.set('metric', params.metric)
  if (params?.enabled !== undefined) qs.set('enabled', String(params.enabled))
  const url = qs.toString() ? `${BASE}/alert-rules?${qs}` : `${BASE}/alert-rules`
  const res = await fetchWithAuth(url)
  if (!res.ok) throw new Error(`fetchAlertRules failed: ${res.status}`)
  return res.json()
}

export async function createAlertRule(data: AlertRuleIn): Promise<AlertRule> {
  const res = await fetchWithAuth(`${BASE}/alert-rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`createAlertRule failed: ${res.status}`)
  return res.json()
}

export async function updateAlertRule(
  id: string,
  data: Partial<AlertRuleIn>,
): Promise<AlertRule> {
  const res = await fetchWithAuth(`${BASE}/alert-rules/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`updateAlertRule failed: ${res.status}`)
  return res.json()
}

export async function deleteAlertRule(id: string): Promise<void> {
  const res = await fetchWithAuth(`${BASE}/alert-rules/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`deleteAlertRule failed: ${res.status}`)
}

// ── Alert Events ────────────────────────────────────────────────────────────

export async function fetchAlerts(
  params?: { agent_name?: string; resolved?: boolean; limit?: number; offset?: number },
): Promise<AlertsResponse> {
  const qs = new URLSearchParams()
  if (params?.agent_name) qs.set('agent_name', params.agent_name)
  if (params?.resolved !== undefined) qs.set('resolved', String(params.resolved))
  if (params?.limit) qs.set('limit', String(params.limit))
  if (params?.offset) qs.set('offset', String(params.offset))
  const url = qs.toString() ? `${BASE}/alerts?${qs}` : `${BASE}/alerts`
  const res = await fetchWithAuth(url)
  if (!res.ok) throw new Error(`fetchAlerts failed: ${res.status}`)
  return res.json()
}

export async function resolveAlert(id: string): Promise<AlertEvent> {
  const res = await fetchWithAuth(`${BASE}/alerts/${id}/resolve`, { method: 'PATCH' })
  if (!res.ok) throw new Error(`resolveAlert failed: ${res.status}`)
  return res.json()
}

export async function fetchAlertsSummary(): Promise<{ unresolved_count: number }> {
  const res = await fetch(`${BASE}/alerts/summary`)
  if (!res.ok) throw new Error(`fetchAlertsSummary failed: ${res.status}`)
  return res.json()
}
