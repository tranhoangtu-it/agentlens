// Prompt Registry page — list templates, view versions, create prompts, add versions, diff

import { useEffect, useState } from 'react'
import { FileText, Plus, ChevronDown, ChevronRight, GitCompare } from 'lucide-react'
import {
  fetchPrompts,
  createPrompt,
  fetchPromptDetail,
  addPromptVersion,
  diffPromptVersions,
  type PromptTemplate,
  type PromptTemplateDetail,
  type PromptDiff,
} from '../lib/prompt-api-client'
import { PromptDiffViewer } from '../components/prompt-diff-viewer'

// ── Sub-components ────────────────────────────────────────────────────────────

function AddVersionForm({
  promptId,
  onAdded,
}: {
  promptId: string
  onAdded: () => void
}) {
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit() {
    if (!content.trim()) return
    setSaving(true)
    try {
      await addPromptVersion(promptId, { content })
      setContent('')
      onAdded()
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Add Version</p>
      <textarea
        rows={4}
        placeholder="Prompt content…"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="w-full bg-background border border-border rounded-md px-3 py-2 text-xs font-mono text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary resize-y"
      />
      <button
        onClick={handleSubmit}
        disabled={saving || !content.trim()}
        className="flex items-center gap-1.5 bg-primary text-primary-foreground rounded-md px-3 py-1.5 text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
      >
        <Plus size={12} />
        Save Version
      </button>
    </div>
  )
}

function DiffPanel({
  promptId,
  latestVersion,
}: {
  promptId: string
  latestVersion: number
}) {
  const [v1, setV1] = useState(1)
  const [v2, setV2] = useState(Math.max(2, latestVersion))
  const [result, setResult] = useState<PromptDiff | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDiff() {
    if (v1 === v2) { setError('v1 and v2 must differ'); return }
    setLoading(true)
    setError(null)
    try {
      const data = await diffPromptVersions(promptId, v1, v2)
      setResult(data)
    } catch {
      setError('Failed to load diff')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-3 space-y-2 border-t border-border pt-3">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1.5">
        <GitCompare size={12} />
        Compare Versions
      </p>
      <div className="flex items-center gap-2">
        <label className="text-xs text-muted-foreground">v1</label>
        <input
          type="number"
          min={1}
          max={latestVersion}
          value={v1}
          onChange={(e) => setV1(Number(e.target.value))}
          className="w-16 bg-background border border-border rounded px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <label className="text-xs text-muted-foreground">v2</label>
        <input
          type="number"
          min={1}
          max={latestVersion}
          value={v2}
          onChange={(e) => setV2(Number(e.target.value))}
          className="w-16 bg-background border border-border rounded px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <button
          onClick={handleDiff}
          disabled={loading}
          className="bg-primary text-primary-foreground rounded-md px-3 py-1 text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Loading…' : 'Diff'}
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {result && <PromptDiffViewer diff={result.diff} v1={result.v1} v2={result.v2} />}
    </div>
  )
}

function PromptRow({ template }: { template: PromptTemplate }) {
  const [expanded, setExpanded] = useState(false)
  const [detail, setDetail] = useState<PromptTemplateDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  async function handleExpand() {
    const next = !expanded
    setExpanded(next)
    if (next && !detail) {
      setLoadingDetail(true)
      try {
        const data = await fetchPromptDetail(template.id)
        setDetail(data)
      } catch {
        // ignore
      } finally {
        setLoadingDetail(false)
      }
    }
  }

  async function refreshDetail() {
    try {
      const data = await fetchPromptDetail(template.id)
      setDetail(data)
    } catch {
      // ignore
    }
  }

  const ChevronIcon = expanded ? ChevronDown : ChevronRight

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <button
        onClick={handleExpand}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-sidebar-accent/40 transition-colors"
      >
        <ChevronIcon size={13} className="text-muted-foreground shrink-0" />
        <FileText size={13} className="text-muted-foreground shrink-0" />
        <span className="flex-1 text-sm font-medium text-foreground">{template.name}</span>
        <span className="text-xs text-muted-foreground shrink-0">
          {template.latest_version === 0 ? 'no versions' : `v${template.latest_version}`}
        </span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-border">
          {loadingDetail && (
            <p className="text-xs text-muted-foreground pt-3">Loading…</p>
          )}
          {detail && (
            <>
              {/* Version list */}
              {detail.versions.length === 0 ? (
                <p className="text-xs text-muted-foreground/60 pt-3">No versions yet.</p>
              ) : (
                <div className="pt-3 space-y-1">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Versions</p>
                  {detail.versions.map((v) => (
                    <div key={v.id} className="bg-background border border-border rounded-md px-3 py-2 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-primary font-semibold">v{v.version}</span>
                        <span className="text-xs text-muted-foreground/60">
                          {new Date(v.created_at).toLocaleString()}
                        </span>
                      </div>
                      <pre className="text-xs font-mono text-foreground/80 whitespace-pre-wrap break-all line-clamp-4">
                        {v.content}
                      </pre>
                    </div>
                  ))}
                </div>
              )}

              {/* Add version form */}
              <AddVersionForm promptId={template.id} onAdded={refreshDetail} />

              {/* Diff panel — only show when at least 2 versions exist */}
              {detail.latest_version >= 2 && (
                <DiffPanel promptId={template.id} latestVersion={detail.latest_version} />
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function PromptRegistryPage() {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([])
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetchPrompts().then((r) => setPrompts(r.prompts)).catch(() => {})
  }, [])

  async function handleCreate() {
    if (!newName.trim()) return
    setCreating(true)
    try {
      await createPrompt(newName.trim())
      setNewName('')
      const updated = await fetchPrompts()
      setPrompts(updated.prompts)
    } catch {
      // ignore
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="p-5 space-y-6 overflow-y-auto max-w-2xl">
      <div className="flex items-center gap-2">
        <FileText size={16} className="text-muted-foreground" />
        <h1 className="text-sm font-semibold text-foreground">Prompt Registry</h1>
      </div>

      {/* Create new template */}
      <div className="bg-card border border-border rounded-lg p-4 space-y-3">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">New Template</h2>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Template name (e.g. summariser)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            className="flex-1 bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button
            onClick={handleCreate}
            disabled={creating || !newName.trim()}
            className="flex items-center gap-1.5 bg-primary text-primary-foreground rounded-md px-3 py-1.5 text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Plus size={12} />
            Create
          </button>
        </div>
      </div>

      {/* Template list */}
      <div className="space-y-2">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Templates</h2>
        {prompts.length === 0 ? (
          <p className="text-xs text-muted-foreground/60">No prompt templates yet.</p>
        ) : (
          <div className="space-y-1.5">
            {prompts.map((p) => (
              <PromptRow key={p.id} template={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
