// API client for AgentLens backend — typed fetch wrappers for traces/spans

export interface Trace {
  id: string
  agent_name: string
  created_at: string
  total_cost_usd: number
  total_tokens: number
  span_count: number
  duration_ms: number
  status: 'completed' | 'running' | 'error'
}

export interface Span {
  id: string
  trace_id: string
  parent_id: string | null
  name: string
  type: 'agent_run' | 'tool_call' | 'llm_call' | 'handoff' | string
  start_ms: number
  end_ms: number
  input: unknown
  output: unknown
  cost_model: string | null
  cost_input_tokens: number
  cost_output_tokens: number
  cost_usd: number
}

export interface TracesResponse {
  traces: Trace[]
  total: number
  limit: number
  offset: number
}

export interface TraceDetailResponse {
  trace: Trace
  spans: Span[]
}

export interface AgentsResponse {
  agents: string[]
}

export interface TraceFilters {
  q?: string
  status?: string
  agent_name?: string
  from_date?: string
  to_date?: string
  min_cost?: number
  max_cost?: number
  sort?: string
  order?: string
  limit?: number
  offset?: number
}

const BASE = '/api'

export async function fetchTraces(filters: TraceFilters = {}): Promise<TracesResponse> {
  const params = new URLSearchParams()
  // Only append defined, non-empty values
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  }
  const qs = params.toString()
  const url = qs ? `${BASE}/traces?${qs}` : `${BASE}/traces`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`fetchTraces failed: ${res.status}`)
  return res.json() as Promise<TracesResponse>
}

export async function fetchAgents(): Promise<AgentsResponse> {
  const res = await fetch(`${BASE}/agents`)
  if (!res.ok) throw new Error(`fetchAgents failed: ${res.status}`)
  return res.json() as Promise<AgentsResponse>
}

export async function fetchTrace(id: string): Promise<TraceDetailResponse> {
  const res = await fetch(`${BASE}/traces/${encodeURIComponent(id)}`)
  if (!res.ok) throw new Error(`fetchTrace failed: ${res.status}`)
  return res.json() as Promise<TraceDetailResponse>
}
