// Eval dashboard — manage criteria, view scores, run evaluations

import { useEffect, useState } from 'react'
import {
  fetchCriteria, createCriteria, deleteCriteria, fetchRuns, fetchScores,
  type EvalCriteria, type EvalRun, type ScoreAggregate, type EvalCriteriaIn,
} from '../lib/eval-api-client'
import { ClipboardCheck, Plus, Trash2, BarChart3 } from 'lucide-react'

export function EvalDashboardPage() {
  const [criteria, setCriteria] = useState<EvalCriteria[]>([])
  const [runs, setRuns] = useState<EvalRun[]>([])
  const [scores, setScores] = useState<ScoreAggregate[]>([])
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    fetchCriteria().then((r) => setCriteria(r.criteria)).catch(() => {})
    fetchRuns({ limit: 20 }).then((r) => setRuns(r.runs)).catch(() => {})
    fetchScores().then((r) => setScores(r.scores)).catch(() => {})
  }, [])

  async function handleCreate(data: EvalCriteriaIn) {
    const c = await createCriteria(data)
    setCriteria((prev) => [c, ...prev])
    setShowForm(false)
  }

  async function handleDelete(id: string) {
    await deleteCriteria(id)
    setCriteria((prev) => prev.filter((c) => c.id !== id))
  }

  function getScore(criteriaId: string): ScoreAggregate | undefined {
    return scores.find((s) => s.criteria_id === criteriaId)
  }

  return (
    <div className="p-5 space-y-6 overflow-y-auto max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ClipboardCheck size={16} className="text-muted-foreground" />
          <h1 className="text-sm font-semibold text-foreground">Evaluations</h1>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 bg-primary text-primary-foreground rounded-md px-3 py-1.5 text-xs font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus size={12} />
          New Criteria
        </button>
      </div>

      {/* Create form */}
      {showForm && <CriteriaForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />}

      {/* Criteria list with scores */}
      <div className="space-y-2">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Criteria</h2>
        {criteria.length === 0 ? (
          <p className="text-xs text-muted-foreground/60">No eval criteria yet.</p>
        ) : (
          <div className="space-y-1">
            {criteria.map((c) => {
              const agg = getScore(c.id)
              return (
                <div key={c.id} className="flex items-center gap-3 bg-card border border-border rounded-md px-3 py-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground font-medium">{c.name}</p>
                    <p className="text-xs text-muted-foreground truncate">{c.description}</p>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                    {c.score_type}
                  </span>
                  {agg && (
                    <div className="flex items-center gap-1 shrink-0">
                      <BarChart3 size={11} className="text-primary" />
                      <span className="text-xs font-mono text-foreground">
                        {agg.avg_score.toFixed(1)}
                      </span>
                      <span className="text-[10px] text-muted-foreground">({agg.run_count})</span>
                    </div>
                  )}
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="text-muted-foreground hover:text-red-400 transition-colors shrink-0"
                    title="Delete"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Recent runs */}
      <div className="space-y-2">
        <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Recent Runs</h2>
        {runs.length === 0 ? (
          <p className="text-xs text-muted-foreground/60">No eval runs yet.</p>
        ) : (
          <div className="space-y-1">
            {runs.map((r) => (
              <div key={r.id} className="flex items-center gap-3 bg-card border border-border rounded-md px-3 py-2">
                <ScoreBadge score={r.score} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-muted-foreground font-mono truncate">{r.trace_id}</p>
                  {r.prompt_name && (
                    <p className="text-[10px] text-muted-foreground">
                      {r.prompt_name} v{r.prompt_version}
                    </p>
                  )}
                </div>
                <p className="text-xs text-muted-foreground/60 shrink-0 max-w-[200px] truncate">
                  {r.reasoning}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 4 ? 'text-green-400' : score >= 3 ? 'text-yellow-400' : 'text-red-400'
  return (
    <span className={`text-sm font-bold font-mono shrink-0 w-8 text-center ${color}`}>
      {score.toFixed(1)}
    </span>
  )
}

function CriteriaForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: EvalCriteriaIn) => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [rubric, setRubric] = useState('')
  const [scoreType, setScoreType] = useState('numeric')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name || !description || !rubric) return
    onSubmit({ name, description, rubric, score_type: scoreType })
  }

  const inputClass = 'w-full bg-background border border-border rounded-md px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary'

  return (
    <form onSubmit={handleSubmit} className="bg-card border border-border rounded-lg p-4 space-y-3">
      <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">New Criteria</h2>
      <input type="text" placeholder="Name (e.g. factual-accuracy)" value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
      <input type="text" placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} className={inputClass} />
      <textarea placeholder="Rubric (scoring instructions for LLM judge)" value={rubric} onChange={(e) => setRubric(e.target.value)} rows={3} className={inputClass} />
      <select value={scoreType} onChange={(e) => setScoreType(e.target.value)} className={inputClass}>
        <option value="numeric">Numeric (1-5)</option>
        <option value="binary">Binary (pass/fail)</option>
      </select>
      <div className="flex gap-2">
        <button type="submit" className="bg-primary text-primary-foreground rounded-md px-3 py-1.5 text-xs font-medium hover:bg-primary/90 transition-colors">
          Create
        </button>
        <button type="button" onClick={onCancel} className="text-xs text-muted-foreground hover:text-foreground transition-colors">
          Cancel
        </button>
      </div>
    </form>
  )
}
