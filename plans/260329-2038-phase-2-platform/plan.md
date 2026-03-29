---
status: approved
planDir: 260329-2038-phase-2-platform
created: 2026-03-29
blockedBy: []
blocks: []
---

# Phase 2: "Platform" — Plugin System + Prompt Versioning + LLM-as-Judge Eval

## Context

Phase 1 shipped killer features (MCP Tracing, AI Autopsy, BYO API Key). Phase 2 builds platform extensibility. Plugin System is foundational — Prompt Versioning and Eval depend on its hooks. Eval reuses the BYO API key infra from Phase 1.

**Source:** `plans/reports/brainstormer-260329-1756-killer-features-roadmap.md`

## Dependency Order

```
Phase 2A: Plugin System        (foundation)
Phase 2B: Prompt Versioning    (independent, can parallel with 2A)
Phase 2C: LLM-as-Judge Eval   (depends on 2A hooks + Phase 1 BYO key)
```

## Phases

| Phase | File | Status | Effort |
|-------|------|--------|--------|
| 2A | [phase-01-plugin-system.md](phase-01-plugin-system.md) | pending | ~2 days |
| 2B | [phase-02-prompt-versioning.md](phase-02-prompt-versioning.md) | pending | ~2 days |
| 2C | [phase-03-llm-eval.md](phase-03-llm-eval.md) | pending | ~3 days |

## Key Decisions

- SDK plugins reuse existing `SpanExporter` protocol + new `SpanProcessor` protocol
- Server plugins auto-discovered from `server/plugins/` directory
- Prompt versions stored as immutable rows, linked to spans via metadata
- Eval reuses `evaluate_alert_rules()` pattern — triggered on trace completion
- Both numeric (1-5) and pass/fail eval scoring supported
- All new features follow existing patterns (alert_*.py → prompt_*.py, eval_*.py)
