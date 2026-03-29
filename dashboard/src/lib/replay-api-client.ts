// API client for replay sandbox sessions

import { fetchWithAuth } from './fetch-with-auth'

const BASE = '/api'

export interface ReplaySession {
  id: string
  trace_id: string
  name: string
  modifications: Record<string, { input?: string }>
  notes: string
  created_at: string
}

export interface ReplaySessionIn {
  trace_id: string
  name?: string
  modifications: Record<string, { input?: string }>
  notes?: string
}

export async function createReplaySession(data: ReplaySessionIn): Promise<ReplaySession> {
  const res = await fetchWithAuth(`${BASE}/replay-sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`Failed: ${res.status}`)
  return res.json()
}

export async function fetchReplaySessions(traceId: string): Promise<{ sessions: ReplaySession[] }> {
  const res = await fetchWithAuth(`${BASE}/traces/${traceId}/replay-sessions`)
  if (!res.ok) throw new Error(`Failed: ${res.status}`)
  return res.json()
}

export async function deleteReplaySession(id: string): Promise<void> {
  await fetchWithAuth(`${BASE}/replay-sessions/${id}`, { method: 'DELETE' })
}
