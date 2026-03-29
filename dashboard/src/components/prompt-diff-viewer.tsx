// Unified diff viewer — highlights added/removed lines from a diff string

interface PromptDiffViewerProps {
  diff: string
  v1: number
  v2: number
}

interface DiffLine {
  type: 'added' | 'removed' | 'context' | 'header'
  text: string
}

function parseDiffLines(diff: string): DiffLine[] {
  if (!diff) return []
  return diff.split('\n').map((line): DiffLine => {
    if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) {
      return { type: 'header', text: line }
    }
    if (line.startsWith('+')) return { type: 'added', text: line }
    if (line.startsWith('-')) return { type: 'removed', text: line }
    return { type: 'context', text: line }
  })
}

export function PromptDiffViewer({ diff, v1, v2 }: PromptDiffViewerProps) {
  const lines = parseDiffLines(diff)

  if (!diff) {
    return (
      <p className="text-xs text-muted-foreground/60 italic">No differences between versions.</p>
    )
  }

  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground font-medium">
        Diff: v{v1} &rarr; v{v2}
      </p>
      <div className="rounded-md border border-border overflow-x-auto bg-background">
        <pre className="text-xs font-mono leading-5 p-3 whitespace-pre-wrap break-all">
          {lines.map((line, i) => {
            if (line.type === 'added') {
              return (
                <span key={i} className="block bg-green-500/15 text-green-400">
                  {line.text}
                </span>
              )
            }
            if (line.type === 'removed') {
              return (
                <span key={i} className="block bg-red-500/15 text-red-400">
                  {line.text}
                </span>
              )
            }
            if (line.type === 'header') {
              return (
                <span key={i} className="block text-muted-foreground/60">
                  {line.text}
                </span>
              )
            }
            return (
              <span key={i} className="block text-foreground/80">
                {line.text}
              </span>
            )
          })}
        </pre>
      </div>
    </div>
  )
}
