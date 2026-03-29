# Phase 2C: LLM-as-Judge Eval

## Overview
- **Priority:** High — enables automated quality assessment
- **Status:** pending
- **Effort:** ~3 days
- **Depends on:** Phase 1 BYO API Key, Phase 2A Plugin System (optional)

## Architecture

### Data Model

```python
class EvalCriteria(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    name: str                              # "factual-accuracy"
    description: str                        # "Is the response factually accurate?"
    rubric: str                             # Scoring instructions for LLM judge
    score_type: str = "numeric"            # "numeric" (1-5) | "binary" (pass/fail)
    agent_name: str = "*"                  # Filter: which agents to eval
    auto_eval: bool = False                # Auto-run on trace completion
    enabled: bool = True
    created_at: datetime

class EvalRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    criteria_id: str = Field(index=True)
    trace_id: str = Field(index=True)
    user_id: str = Field(index=True)
    score: float                            # 1-5 or 0/1
    reasoning: str                          # LLM judge explanation
    llm_provider: str
    llm_model: str
    prompt_name: str | None = None          # Link to prompt version if available
    prompt_version: int | None = None
    created_at: datetime
    __table_args__ = (
        Index("ix_eval_criteria_trace", "criteria_id", "trace_id"),
        Index("ix_eval_user_created", "user_id", "created_at"),
    )
```

### Flow

1. User defines eval criteria via dashboard (name, rubric, score_type)
2. User selects traces → "Run Eval" or enable auto_eval
3. Server extracts final output from trace spans
4. Builds judge prompt: criteria + rubric + agent output
5. Calls LLM via BYO API key (reuse `llm_provider.py` from Phase 1)
6. Stores score + reasoning in EvalRun
7. Dashboard shows scores, trends, comparison across prompt versions

## Files to Create

| File | Lines | Purpose |
|------|-------|---------|
| `server/eval_models.py` | ~70 | EvalCriteria + EvalRun tables + schemas |
| `server/eval_storage.py` | ~80 | CRUD for criteria + runs |
| `server/eval_runner.py` | ~100 | Build judge prompt, call LLM, parse score |
| `server/eval_routes.py` | ~120 | REST API for eval management + execution |
| `dashboard/src/lib/eval-api-client.ts` | ~70 | API client |
| `dashboard/src/pages/eval-dashboard-page.tsx` | ~200 | Criteria list, run results, score trends |
| `dashboard/src/components/eval-score-card.tsx` | ~80 | Score display component |
| `dashboard/src/components/eval-criteria-editor.tsx` | ~120 | Create/edit criteria form |
| `server/tests/test_eval.py` | ~100 | CRUD + eval execution tests |

## Files to Modify

| File | Change |
|------|--------|
| `server/main.py` | Import + include eval_router, call auto_eval on trace completion |
| `server/tests/conftest.py` | Import EvalCriteria, EvalRun for table creation |
| `dashboard/src/App.tsx` | Add 'evals' route + nav item |

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/eval/criteria` | List eval criteria |
| POST | `/api/eval/criteria` | Create criteria |
| PUT | `/api/eval/criteria/{id}` | Update criteria |
| DELETE | `/api/eval/criteria/{id}` | Delete criteria |
| POST | `/api/eval/run` | Run eval on specific trace(s) |
| GET | `/api/eval/runs` | List eval runs (filterable) |
| GET | `/api/eval/runs/{id}` | Get single eval run detail |
| GET | `/api/eval/scores` | Aggregate scores (for charts) |

## Implementation Steps

1. Create `server/eval_models.py`
2. Create `server/eval_storage.py`
3. Create `server/eval_runner.py` — reuse `llm_provider.call_llm()` from Phase 1
4. Create `server/eval_routes.py`
5. Register router in `server/main.py`
6. Add auto-eval trigger in trace ingestion (same pattern as `evaluate_alert_rules`)
7. Write `server/tests/test_eval.py` → run pytest
8. Create dashboard: eval-api-client, eval-dashboard-page, eval-score-card, eval-criteria-editor
9. Add route + nav in `App.tsx`
10. TypeScript check + build

## Key Details

- **Judge prompt template:**
  ```
  System: You are an evaluation judge. Score the following agent output.
  Criteria: {criteria.description}
  Rubric: {criteria.rubric}
  Score type: {numeric 1-5 | pass/fail}

  Agent output: {trace output}

  Respond with JSON: {"score": <number>, "reasoning": "<explanation>"}
  ```
- **Auto-eval:** When `auto_eval=True`, runs after trace completion (same hook as alerts)
- **Score aggregation:** `/api/eval/scores` returns avg scores grouped by criteria + time period
- **Prompt version link:** If span metadata contains `prompt_name`/`prompt_version`, store in EvalRun for cross-version comparison
- **Reuse:** `llm_provider.py` (LLM calls), `settings_storage.get_decrypted_api_key()` (BYO key)
- **Rate limit:** Max 5 concurrent eval runs per user (prevent API key abuse)

## Success Criteria
- [ ] CRUD for eval criteria works
- [ ] Eval execution calls LLM and stores score
- [ ] Auto-eval triggers on trace completion
- [ ] Dashboard shows scores and trends
- [ ] Prompt version comparison visible in eval results
