# Phase 2B: Prompt Versioning

## Overview
- **Priority:** High — enables prompt A/B testing and eval comparison
- **Status:** pending
- **Effort:** ~2 days

## Architecture

### Data Model

```python
class PromptTemplate(SQLModel, table=True):
    id: str = Field(primary_key=True)       # deterministic: hash(user_id + name)
    user_id: str = Field(index=True)
    name: str                                # "agent-system-prompt"
    latest_version: int = 0
    created_at: datetime
    updated_at: datetime
    __table_args__ = (Index("ix_prompt_user_name", "user_id", "name", unique=True),)

class PromptVersion(SQLModel, table=True):
    id: str = Field(primary_key=True)
    prompt_id: str = Field(index=True)
    user_id: str = Field(index=True)
    version: int
    content: str                             # full prompt text
    variables_json: str = "[]"              # ["{{name}}", "{{context}}"]
    metadata_json: str = "{}"               # git commit, author, etc.
    created_at: datetime
    __table_args__ = (Index("ix_pv_prompt_version", "prompt_id", "version", unique=True),)
```

### SDK Integration

```python
# Usage in user code
with agentlens.trace("my-agent"):
    prompt = agentlens.prompt("system-prompt", version=3)
    # prompt content logged in span metadata as prompt_name + prompt_version
```

## Files to Create

| File | Lines | Purpose |
|------|-------|---------|
| `server/prompt_models.py` | ~60 | PromptTemplate + PromptVersion tables + schemas |
| `server/prompt_storage.py` | ~80 | CRUD: create template, add version, list, get, diff |
| `server/prompt_routes.py` | ~100 | REST API for prompt management |
| `dashboard/src/lib/prompt-api-client.ts` | ~60 | API client |
| `dashboard/src/pages/prompt-registry-page.tsx` | ~180 | List prompts, versions, usage |
| `dashboard/src/components/prompt-diff-viewer.tsx` | ~100 | Side-by-side version diff |
| `server/tests/test_prompt.py` | ~80 | CRUD + versioning tests |

## Files to Modify

| File | Change |
|------|--------|
| `server/main.py` | Import + include prompt_router |
| `server/tests/conftest.py` | Import PromptTemplate, PromptVersion for table creation |
| `dashboard/src/App.tsx` | Add 'prompts' route + nav item |
| `sdk/agentlens/tracer.py` | Add `prompt()` method to log prompt usage in span metadata |
| `sdk/agentlens/__init__.py` | Export `prompt` function |

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/prompts` | List prompt templates |
| POST | `/api/prompts` | Create template |
| GET | `/api/prompts/{id}` | Get template + versions |
| POST | `/api/prompts/{id}/versions` | Add new version |
| GET | `/api/prompts/{id}/versions/{v}` | Get specific version |
| GET | `/api/prompts/{id}/diff?v1=1&v2=2` | Diff two versions |

## Implementation Steps

1. Create `server/prompt_models.py`
2. Create `server/prompt_storage.py`
3. Create `server/prompt_routes.py`
4. Register router in `server/main.py`
5. Write `server/tests/test_prompt.py` → run pytest
6. Add `prompt()` to SDK tracer (logs prompt_name + version in span metadata)
7. Create dashboard API client + prompt registry page + diff viewer
8. Add route + nav item in `App.tsx`
9. TypeScript check dashboard

## Key Details

- **Immutable versions:** Once created, a version's content never changes
- **Version auto-increment:** POST to `/versions` auto-assigns next version number
- **Prompt diff:** Simple line-by-line diff (reuse `difflib` server-side)
- **SDK `prompt()` method:** Returns content string, logs `{prompt_name, prompt_version}` in current span metadata
- **No server-side prompt storage from SDK:** SDK just logs metadata. User manages prompts via dashboard.

## Success Criteria
- [ ] CRUD for prompt templates and versions works
- [ ] Version diffing returns meaningful output
- [ ] SDK `prompt()` logs metadata in active span
- [ ] Dashboard shows prompt list with version history
