// API client for LLM-as-Judge evaluations

import { fetchWithAuth } from './fetch-with-auth'

const BASE = '/api/eval'

export interface EvalCriteria {
  id: string
  name: string
  description: string
  rubric: string
  score_type: 'numeric' | 'binary'
  agent_name: string
  auto_eval: boolean
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface EvalRun {
  id: string
  criteria_id: string
  trace_id: string
  score: number
  reasoning: string
  llm_provider: string
  llm_model: string
  prompt_name: string | null
  prompt_version: number | null
  created_at: string
}

export interface EvalCriteriaIn {
  name: string
  description: string
  rubric: string
  score_type?: string
  agent_name?: string
  auto_eval?: boolean
}

export interface ScoreAggregate {
  criteria_id: string
  avg_score: number
  run_count: number
}

export async function fetchCriteria(agentName?: string): Promise<{ criteria: EvalCriteria[] }> {
  const qs = agentName ? `?agent_name=${agentName}` : ''
  const res = await fetchWithAuth(`${BASE}/criteria${qs}`)
  if (!res.ok) throw new Error(`fetchCriteria failed: ${res.status}`)
  return res.json()
}

export async function createCriteria(data: EvalCriteriaIn): Promise<EvalCriteria> {
  const res = await fetchWithAuth(`${BASE}/criteria`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`createCriteria failed: ${res.status}`)
  return res.json()
}

export async function deleteCriteria(id: string): Promise<void> {
  const res = await fetchWithAuth(`${BASE}/criteria/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`deleteCriteria failed: ${res.status}`)
}

export async function runEval(criteriaId: string, traceIds: string[]): Promise<{ runs: EvalRun[]; count: number }> {
  const res = await fetchWithAuth(`${BASE}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ criteria_id: criteriaId, trace_ids: traceIds }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Eval failed' }))
    throw new Error(err.detail || `Eval failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchRuns(params?: {
  criteria_id?: string; trace_id?: string; limit?: number; offset?: number
}): Promise<{ runs: EvalRun[]; total: number }> {
  const qs = new URLSearchParams()
  if (params?.criteria_id) qs.set('criteria_id', params.criteria_id)
  if (params?.trace_id) qs.set('trace_id', params.trace_id)
  if (params?.limit) qs.set('limit', String(params.limit))
  if (params?.offset) qs.set('offset', String(params.offset))
  const url = qs.toString() ? `${BASE}/runs?${qs}` : `${BASE}/runs`
  const res = await fetchWithAuth(url)
  if (!res.ok) throw new Error(`fetchRuns failed: ${res.status}`)
  return res.json()
}

export async function fetchScores(criteriaId?: string): Promise<{ scores: ScoreAggregate[] }> {
  const qs = criteriaId ? `?criteria_id=${criteriaId}` : ''
  const res = await fetchWithAuth(`${BASE}/scores${qs}`)
  if (!res.ok) throw new Error(`fetchScores failed: ${res.status}`)
  return res.json()
}
