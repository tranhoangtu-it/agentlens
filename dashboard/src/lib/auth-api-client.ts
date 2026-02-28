// API client for auth endpoints — login, register, me, api-keys

import { fetchWithAuth } from './fetch-with-auth'

const BASE = '/api/auth'

export interface AuthUser {
  user_id: string
  email: string
  display_name?: string
  is_admin: boolean
}

export interface ApiKeyInfo {
  id: string
  key_prefix: string
  name: string
  created_at: string
  last_used_at: string | null
}

export async function login(email: string, password: string): Promise<{ user_id: string; email: string; token: string }> {
  const res = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed' }))
    throw new Error(err.detail || 'Login failed')
  }
  return res.json()
}

export async function register(
  email: string,
  password: string,
  displayName?: string,
): Promise<{ user_id: string; email: string; token: string }> {
  const res = await fetch(`${BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed' }))
    throw new Error(err.detail || 'Registration failed')
  }
  return res.json()
}

export async function fetchMe(): Promise<AuthUser> {
  const res = await fetchWithAuth(`${BASE}/me`)
  if (!res.ok) throw new Error('Not authenticated')
  return res.json()
}

export async function createApiKey(name: string = 'default'): Promise<{ id: string; key: string; key_prefix: string; name: string; created_at: string }> {
  const res = await fetchWithAuth(`${BASE}/api-keys?name=${encodeURIComponent(name)}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to create API key')
  return res.json()
}

export async function fetchApiKeys(): Promise<{ keys: ApiKeyInfo[] }> {
  const res = await fetchWithAuth(`${BASE}/api-keys`)
  if (!res.ok) throw new Error('Failed to fetch API keys')
  return res.json()
}

export async function deleteApiKey(keyId: string): Promise<void> {
  const res = await fetchWithAuth(`${BASE}/api-keys/${keyId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete API key')
}
