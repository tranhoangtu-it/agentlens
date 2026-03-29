// Replay sandbox panel — edit span inputs and view modifications

import { memo, useState } from 'react'
import { ScrollArea } from './ui/scroll-area'
import { X, Save, Pencil, RotateCcw } from 'lucide-react'
import type { Span } from '../lib/api-client'

interface Props {
  span: Span
  modification: { input?: string } | null
  onModify: (spanId: string, input: string) => void
  onReset: (spanId: string) => void
  onClose: () => void
}

export const ReplaySandboxPanel = memo(function ReplaySandboxPanel({
  span, modification, onModify, onReset, onClose,
}: Props) {
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState('')
  const isModified = modification != null
  const currentInput = isModified ? modification.input : (typeof span.input === 'string' ? span.input : JSON.stringify(span.input))

  function startEdit() {
    setEditValue(currentInput || '')
    setEditing(true)
  }

  function saveEdit() {
    onModify(span.id, editValue)
    setEditing(false)
  }

  return (
    <aside className="w-80 shrink-0 bg-card border-l border-border flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground truncate pr-2 flex items-center gap-2">
          {span.name}
          {isModified && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-400">modified</span>
          )}
        </h3>
        <button onClick={onClose} className="p-1 text-muted-foreground hover:text-foreground transition-colors">
          <X size={14} />
        </button>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-4 py-3 space-y-3">
          {/* Span info */}
          <div className="text-xs text-muted-foreground space-y-1">
            <p>Type: <span className="text-foreground">{span.type}</span></p>
            <p>Duration: <span className="text-foreground">{span.end_ms - span.start_ms}ms</span></p>
          </div>

          {/* Input section — editable */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Input</p>
              <div className="flex items-center gap-1">
                {!editing && (
                  <button onClick={startEdit} className="p-1 text-muted-foreground hover:text-foreground transition-colors" title="Edit input">
                    <Pencil size={11} />
                  </button>
                )}
                {isModified && !editing && (
                  <button onClick={() => onReset(span.id)} className="p-1 text-muted-foreground hover:text-yellow-400 transition-colors" title="Reset to original">
                    <RotateCcw size={11} />
                  </button>
                )}
              </div>
            </div>

            {editing ? (
              <div className="space-y-2">
                <textarea
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  rows={6}
                  className="w-full bg-background border border-primary/40 rounded-md px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-y"
                />
                <div className="flex gap-2">
                  <button onClick={saveEdit} className="flex items-center gap-1 bg-primary text-primary-foreground rounded px-2 py-1 text-[10px] font-medium hover:bg-primary/90 transition-colors">
                    <Save size={10} /> Save
                  </button>
                  <button onClick={() => setEditing(false)} className="text-[10px] text-muted-foreground hover:text-foreground transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className={`rounded-md border p-3 text-xs font-mono whitespace-pre-wrap max-h-48 overflow-y-auto ${isModified ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-border bg-card'}`}>
                {currentInput || '—'}
              </div>
            )}

            {/* Show original if modified */}
            {isModified && !editing && (
              <div className="mt-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Original</p>
                <div className="rounded-md border border-border bg-card p-3 text-xs font-mono whitespace-pre-wrap max-h-32 overflow-y-auto text-muted-foreground">
                  {typeof span.input === 'string' ? span.input : JSON.stringify(span.input) || '—'}
                </div>
              </div>
            )}
          </div>

          {/* Output (read-only) */}
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1.5">Output</p>
            <div className="rounded-md border border-border bg-card p-3 text-xs font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
              {typeof span.output === 'string' ? span.output : JSON.stringify(span.output) || '—'}
            </div>
          </div>
        </div>
      </ScrollArea>
    </aside>
  )
})
