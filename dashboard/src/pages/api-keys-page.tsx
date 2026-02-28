// API Keys management page — list, create, delete keys

import { useEffect, useState } from 'react'
import { createApiKey, deleteApiKey, fetchApiKeys, type ApiKeyInfo } from '../lib/auth-api-client'
import { Copy, Key, Plus, Trash2 } from 'lucide-react'

export function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyInfo[]>([])
  const [newKeyName, setNewKeyName] = useState('')
  const [newFullKey, setNewFullKey] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetchApiKeys().then((r) => setKeys(r.keys)).catch(() => {})
  }, [])

  async function handleCreate() {
    setCreating(true)
    try {
      const result = await createApiKey(newKeyName || 'default')
      setNewFullKey(result.key)
      setNewKeyName('')
      const updated = await fetchApiKeys()
      setKeys(updated.keys)
    } catch {
      // ignore
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(keyId: string) {
    try {
      await deleteApiKey(keyId)
      setKeys((prev) => prev.filter((k) => k.id !== keyId))
    } catch {
      // ignore
    }
  }

  function handleCopy() {
    if (newFullKey) {
      navigator.clipboard.writeText(newFullKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="p-5 space-y-6 overflow-y-auto max-w-2xl">
      <div className="flex items-center gap-2">
        <Key size={16} className="text-muted-foreground" />
        <h1 className="text-sm font-semibold text-foreground">API Keys</h1>
      </div>

      {/* Create new key */}
      <div className="bg-card border border-border rounded-lg p-4 space-y-3">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Create New Key</h2>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Key name (e.g. my-agent)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            className="flex-1 bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button
            onClick={handleCreate}
            disabled={creating}
            className="flex items-center gap-1.5 bg-primary text-primary-foreground rounded-md px-3 py-1.5 text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Plus size={12} />
            Create
          </button>
        </div>

        {/* Show full key once */}
        {newFullKey && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-md p-3 space-y-1.5">
            <p className="text-xs text-green-400 font-medium">Key created! Copy it now — it won't be shown again.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs font-mono text-foreground bg-background rounded px-2 py-1 break-all">
                {newFullKey}
              </code>
              <button
                onClick={handleCopy}
                className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                title="Copy"
              >
                <Copy size={14} />
              </button>
            </div>
            {copied && <p className="text-xs text-green-400">Copied!</p>}
          </div>
        )}
      </div>

      {/* Existing keys */}
      <div className="space-y-2">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Your Keys</h2>
        {keys.length === 0 ? (
          <p className="text-xs text-muted-foreground/60">No API keys yet.</p>
        ) : (
          <div className="space-y-1">
            {keys.map((k) => (
              <div key={k.id} className="flex items-center gap-3 bg-card border border-border rounded-md px-3 py-2">
                <Key size={12} className="text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate">{k.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{k.key_prefix}</p>
                </div>
                <span className="text-xs text-muted-foreground/60 shrink-0">
                  {k.last_used_at ? `Used ${new Date(k.last_used_at).toLocaleDateString()}` : 'Never used'}
                </span>
                <button
                  onClick={() => handleDelete(k.id)}
                  className="text-muted-foreground hover:text-red-400 transition-colors shrink-0"
                  title="Delete key"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
