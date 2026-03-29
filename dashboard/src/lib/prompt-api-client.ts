// API client for prompt template versioning

import { fetchWithAuth } from './fetch-with-auth'

const BASE = '/api'

export interface PromptTemplate {
  id: string
  user_id: string
  name: string
  latest_version: number
  created_at: string
  updated_at: string
}

export interface PromptVersion {
  id: string
  prompt_id: string
  version: number
  content: string
  variables_json: string
  metadata_json: string
  created_at: string
}

export interface PromptTemplateDetail extends PromptTemplate {
  versions: PromptVersion[]
}

export interface PromptVersionIn {
  content: string
  variables?: string[]
  metadata?: Record<string, unknown>
}

export interface PromptDiff {
  v1: number
  v2: number
  diff: string
}

// ── Templates ────────────────────────────────────────────────────────────────

export async function fetchPrompts(): Promise<{ prompts: PromptTemplate[] }> {
  const res = await fetchWithAuth(`${BASE}/prompts`)
  if (!res.ok) throw new Error(`fetchPrompts failed: ${res.status}`)
  return res.json()
}

export async function createPrompt(name: string): Promise<PromptTemplate> {
  const res = await fetchWithAuth(`${BASE}/prompts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error(`createPrompt failed: ${res.status}`)
  return res.json()
}

export async function fetchPromptDetail(id: string): Promise<PromptTemplateDetail> {
  const res = await fetchWithAuth(`${BASE}/prompts/${id}`)
  if (!res.ok) throw new Error(`fetchPromptDetail failed: ${res.status}`)
  return res.json()
}

// ── Versions ─────────────────────────────────────────────────────────────────

export async function addPromptVersion(
  promptId: string,
  data: PromptVersionIn,
): Promise<PromptVersion> {
  const res = await fetchWithAuth(`${BASE}/prompts/${promptId}/versions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`addPromptVersion failed: ${res.status}`)
  return res.json()
}

export async function fetchPromptVersion(
  promptId: string,
  version: number,
): Promise<PromptVersion> {
  const res = await fetchWithAuth(`${BASE}/prompts/${promptId}/versions/${version}`)
  if (!res.ok) throw new Error(`fetchPromptVersion failed: ${res.status}`)
  return res.json()
}

export async function diffPromptVersions(
  promptId: string,
  v1: number,
  v2: number,
): Promise<PromptDiff> {
  const res = await fetchWithAuth(`${BASE}/prompts/${promptId}/diff?v1=${v1}&v2=${v2}`)
  if (!res.ok) throw new Error(`diffPromptVersions failed: ${res.status}`)
  return res.json()
}
